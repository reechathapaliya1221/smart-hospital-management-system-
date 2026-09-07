from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from .models import Department, Token
from datetime import datetime
from .utils.sms import send_token_sms, send_ready_sms, send_cancelled_sms

def index(request):
    departments = Department.objects.filter(is_active=True)
    total_waiting = Token.objects.filter(status='waiting').count()
    today_tokens = Token.objects.filter(created_at__date=timezone.now().date()).count()
    in_progress = Token.objects.filter(status='in_progress').count()
    
    # Calculate average wait time
    completed_today = Token.objects.filter(
        status='completed',
        created_at__date=timezone.now().date()
    )
    avg_wait = 0
    if completed_today.exists():
        total_wait = sum([t.actual_wait_time or 0 for t in completed_today])
        avg_wait = total_wait // completed_today.count()
    
    context = {
        'departments': departments,
        'total_waiting': total_waiting,
        'today_tokens': today_tokens,
        'in_progress': in_progress,
        'avg_wait': avg_wait,
    }
    return render(request, 'queue_system/index.html', context)

def get_token(request):
    """Generate new token for patient"""
    if request.method == 'POST':
        department_id = request.POST.get('department')
        patient_name = request.POST.get('patient_name')
        patient_phone = request.POST.get('patient_phone')
        patient_email = request.POST.get('patient_email', '')
        priority = request.POST.get('priority', 'normal')
        
        department = get_object_or_404(Department, id=department_id)
        
        # Calculate predicted wait time
        waiting_count = Token.objects.filter(department=department, status='waiting').count()
        in_progress_count = Token.objects.filter(department=department, status='in_progress').count()
        
        # Simple prediction algorithm
        base_time = department.average_consultation_time
        priority_multiplier = {'normal': 1, 'urgent': 0.7, 'emergency': 0.3}.get(priority, 1)
        predicted_time = int((waiting_count * base_time + in_progress_count * (base_time/2)) * priority_multiplier)
        predicted_time = max(5, min(120, predicted_time))  # Between 5-120 minutes
        
        # Create token
        token = Token.objects.create(
            department=department,
            patient_name=patient_name,
            patient_phone=patient_phone,
            patient_email=patient_email,
            priority=priority,
            predicted_wait_time=predicted_time
        )
        
        # Send SMS confirmation
        sms_sent = send_token_sms(patient_phone, token.token_number, patient_name, predicted_time)
        
        if sms_sent:
            messages.success(request, f'✓ Token {token.token_number} created successfully! SMS sent to {patient_phone}')
        else:
            messages.warning(request, f'✓ Token {token.token_number} created but SMS could not be sent')
        
        messages.info(request, f'Estimated wait time: {predicted_time} minutes')
        
        return redirect('my_ticket', token_id=token.id)
    
    departments = Department.objects.filter(is_active=True)
    return render(request, 'queue_system/get_token.html', {'departments': departments})

def queue_status(request):
    """Live queue status page"""
    departments = Department.objects.filter(is_active=True)
    department_data = []
    
    for dept in departments:
        waiting_tokens = Token.objects.filter(
            department=dept, 
            status='waiting'
        ).order_by('-priority', 'created_at')
        
        in_progress_token = Token.objects.filter(
            department=dept, 
            status='in_progress'
        ).first()
        
        queue_list = []
        cumulative_time = 0
        
        for idx, token in enumerate(waiting_tokens):
            queue_list.append({
                'token': token,
                'position': idx + 1,
                'estimated_wait': token.predicted_wait_time,
                'cumulative_wait': cumulative_time,
            })
            cumulative_time += token.predicted_wait_time // 2
        
        department_data.append({
            'department': dept,
            'waiting_count': waiting_tokens.count(),
            'in_progress': in_progress_token,
            'queue': queue_list,
        })
    
    # Statistics
    total_waiting = sum(d['waiting_count'] for d in department_data)
    total_in_progress = Token.objects.filter(status='in_progress').count()
    total_completed_today = Token.objects.filter(
        status='completed',
        created_at__date=timezone.now().date()
    ).count()
    
    context = {
        'departments': department_data,
        'total_waiting': total_waiting,
        'total_in_progress': total_in_progress,
        'total_completed_today': total_completed_today,
        'last_updated': timezone.now(),
    }
    return render(request, 'queue_system/queue_status.html', context)

def my_ticket(request, token_id):
    """Display patient's ticket details"""
    token = get_object_or_404(Token, id=token_id)
    position = token.get_position()
    
    # Calculate updated estimated time
    remaining_time = 0
    if token.status == 'waiting':
        waiting_ahead = Token.objects.filter(
            department=token.department,
            status='waiting',
            created_at__lt=token.created_at
        ).count()
        remaining_time = waiting_ahead * token.department.average_consultation_time
    
    context = {
        'token': token,
        'position': position,
        'remaining_time': remaining_time,
    }
    return render(request, 'queue_system/my_ticket.html', context)

@staff_member_required
def admin_dashboard(request):
    """Admin dashboard for managing queue"""
    if request.method == 'POST':
        action = request.POST.get('action')
        token_id = request.POST.get('token_id')
        token = get_object_or_404(Token, id=token_id)
        
        if action == 'start':
            token.status = 'in_progress'
            token.start_time = timezone.now()
            token.save()
            
            # Send SMS notification that token is ready
            sms_sent = send_ready_sms(token.patient_phone, token.token_number, token.department.name)
            
            if sms_sent:
                messages.success(request, f'Started service for {token.token_number} - SMS sent to patient')
            else:
                messages.success(request, f'Started service for {token.token_number} - SMS failed')
            
        elif action == 'complete':
            token.status = 'completed'
            token.end_time = timezone.now()
            if token.start_time:
                wait_minutes = int((token.start_time - token.created_at).total_seconds() / 60)
                token.actual_wait_time = wait_minutes
            token.save()
            messages.success(request, f'Completed {token.token_number}')
            
        elif action == 'cancel':
            token.status = 'cancelled'
            token.save()
            
            # Send cancellation SMS
            sms_sent = send_cancelled_sms(token.patient_phone, token.token_number)
            
            if sms_sent:
                messages.warning(request, f'Cancelled {token.token_number} - SMS sent to patient')
            else:
                messages.warning(request, f'Cancelled {token.token_number}')
            
        elif action == 'call_next':
            department_id = request.POST.get('department_id')
            department = get_object_or_404(Department, id=department_id)
            next_token = Token.objects.filter(
                department=department,
                status='waiting'
            ).order_by('-priority', 'created_at').first()
            
            if next_token:
                next_token.status = 'in_progress'
                next_token.start_time = timezone.now()
                next_token.save()
                
                # Send SMS to next patient
                sms_sent = send_ready_sms(next_token.patient_phone, next_token.token_number, department.name)
                
                if sms_sent:
                    messages.success(request, f'Called next patient: {next_token.token_number} - SMS sent')
                else:
                    messages.success(request, f'Called next patient: {next_token.token_number}')
            else:
                messages.info(request, 'No patients waiting')
        
        return redirect('admin_dashboard')
    
    # Get all active tokens
    tokens = Token.objects.filter(
        status__in=['waiting', 'in_progress']
    ).select_related('department').order_by('-priority', 'created_at')
    
    departments = Department.objects.filter(is_active=True)
    
    # Statistics
    stats = {
        'total_today': Token.objects.filter(created_at__date=timezone.now().date()).count(),
        'completed_today': Token.objects.filter(
            status='completed',
            created_at__date=timezone.now().date()
        ).count(),
        'waiting_now': Token.objects.filter(status='waiting').count(),
        'in_progress_now': Token.objects.filter(status='in_progress').count(),
    }
    
    context = {
        'tokens': tokens,
        'departments': departments,
        'stats': stats,
    }
    return render(request, 'queue_system/admin_dashboard.html', context)

# API Endpoints
def api_queue_status(request):
    """REST API for queue status"""
    department_id = request.GET.get('department_id')
    
    if department_id:
        department = get_object_or_404(Department, id=department_id)
        waiting_tokens = Token.objects.filter(department=department, status='waiting')
        
        data = {
            'department': department.name,
            'waiting_count': waiting_tokens.count(),
            'queue': [
                {
                    'token': t.token_number,
                    'patient': t.patient_name,
                    'position': idx + 1,
                    'estimated_wait': t.predicted_wait_time
                }
                for idx, t in enumerate(waiting_tokens)
            ]
        }
    else:
        data = {
            'departments': [
                {
                    'id': d.id,
                    'name': d.name,
                    'waiting': d.get_waiting_count(),
                    'estimated_wait': d.get_waiting_count() * d.average_consultation_time
                }
                for d in Department.objects.filter(is_active=True)
            ]
        }
    
    return JsonResponse(data)
@staff_member_required
def resend_sms(request, token_id):
    """Resend SMS notification for a token"""
    token = get_object_or_404(Token, id=token_id)
    
    if token.status == 'waiting':
        sms_sent = send_token_sms(token.patient_phone, token.token_number, token.patient_name, token.predicted_wait_time)
        message = f'SMS resent to {token.patient_phone}' if sms_sent else 'Failed to resend SMS'
    elif token.status == 'in_progress':
        sms_sent = send_ready_sms(token.patient_phone, token.token_number, token.department.name)
        message = f'Ready notification resent to {token.patient_phone}' if sms_sent else 'Failed to resend SMS'
    else:
        message = 'Cannot send SMS for this token status'
        sms_sent = False
    
    if sms_sent:
        messages.success(request, message)
    else:
        messages.error(request, message)
    
    return redirect('admin_dashboard')