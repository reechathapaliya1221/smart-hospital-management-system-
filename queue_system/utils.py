from twilio.rest import Client
from django.conf import settings
from django.core.mail import send_mail
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import logging
from .models import Department, Token
from django.utils import timezone

logger = logging.getLogger(__name__)

def send_sms_notification(phone_number, message):
    """Send SMS using Twilio"""
    try:
        if settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN:
            client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            
            message = client.messages.create(
                body=message,
                from_=settings.TWILIO_PHONE_NUMBER,
                to=phone_number
            )
            logger.info(f"SMS sent to {phone_number}, SID: {message.sid}")
            return True
        else:
            # Mock SMS for development
            logger.info(f"MOCK SMS to {phone_number}: {message}")
            return True
    except Exception as e:
        logger.error(f"Failed to send SMS: {str(e)}")
        return False

def send_email_notification(email, subject, message):
    """Send email notification"""
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@hospital.com',
            [email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        logger.error(f"Failed to send email: {str(e)}")
        return False

def update_realtime_queue(department_id):
    """Update real-time queue status via WebSocket"""
    try:
        department = Department.objects.get(id=department_id)
        waiting_tokens = Token.objects.filter(
            department=department,
            status='waiting'
        ).order_by('-priority', 'created_at')
        
        in_progress_token = Token.objects.filter(
            department=department,
            status='in_progress'
        ).first()
        
        queue_data = {
            'department_id': department.id,
            'department_name': department.name,
            'waiting_count': waiting_tokens.count(),
            'current_token': in_progress_token.token_number if in_progress_token else None,
            'queue': [
                {
                    'token': token.token_number,
                    'patient': token.patient_name,
                    'priority': token.priority,
                    'position': idx + 1,
                    'estimated_wait': token.predicted_wait_time
                }
                for idx, token in enumerate(waiting_tokens[:10])  # Send first 10 for performance
            ],
            'timestamp': timezone.now().isoformat()
        }
        
        # Send to WebSocket group
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"department_{department_id}",
            {
                'type': 'queue_update',
                'data': queue_data
            }
        )
        
        # Also send to global group
        async_to_sync(channel_layer.group_send)(
            "global_queue",
            {
                'type': 'queue_update',
                'data': queue_data
            }
        )
        
        logger.info(f"Real-time update sent for department {department.name}")
        return True
    except Exception as e:
        logger.error(f"Failed to send real-time update: {str(e)}")
        return False

def generate_token_qr(token):
    """Generate QR code for token"""
    import qrcode
    from io import BytesIO
    from django.core.files import File
    
    qr_data = f"""
    Hospital Token
    Token: {token.token_number}
    Department: {token.department.name}
    Patient: {token.patient_name}
    Date: {token.created_at.strftime('%Y-%m-%d %H:%M')}
    Status: {token.get_status_display()}
    """
    
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(qr_data)
    qr.make(fit=True)
    
    img = qr.make_image(fill='black', back_color='white')
    blob = BytesIO()
    img.save(blob, 'PNG')
    
    filename = f"qr_{token.token_number}.png"
    token.qr_code.save(filename, File(blob), save=True)
    
    return token.qr_code.url if token.qr_code else None

def calculate_queue_metrics(department_id):
    """Calculate various queue metrics"""
    department = Department.objects.get(id=department_id)
    
    waiting_tokens = Token.objects.filter(
        department=department,
        status='waiting'
    )
    
    in_progress_tokens = Token.objects.filter(
        department=department,
        status='in_progress'
    )
    
    completed_today = Token.objects.filter(
        department=department,
        status='completed',
        created_at__date=timezone.now().date()
    ).count()
    
    # Calculate average service time
    avg_service_time = Token.objects.filter(
        department=department,
        start_time__isnull=False,
        end_time__isnull=False
    ).aggregate(
        avg_time=models.Avg(
            models.F('end_time') - models.F('start_time'),
            output_field=models.DurationField()
        )
    )['avg_time']
    
    if avg_service_time:
        avg_service_minutes = avg_service_time.total_seconds() / 60
    else:
        avg_service_minutes = department.average_consultation_time
    
    # Predict wait time for new patient
    if waiting_tokens.count() > 0:
        predicted_wait = waiting_tokens.count() * avg_service_minutes
    else:
        predicted_wait = avg_service_minutes
    
    return {
        'waiting_count': waiting_tokens.count(),
        'in_progress_count': in_progress_tokens.count(),
        'completed_today': completed_today,
        'average_service_time': round(avg_service_minutes, 2),
        'predicted_wait_for_new': round(predicted_wait, 2),
        'utilization_rate': round(
            (in_progress_tokens.count() / (in_progress_tokens.count() + waiting_tokens.count() or 1)) * 100, 2
        )
    }