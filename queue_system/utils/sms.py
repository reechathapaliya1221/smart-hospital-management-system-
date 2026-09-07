# queue_system/utils/sms.py
"""
SMS Utility Module for Smart Hospital Queue System
Handles all SMS notifications using Twilio
"""

import logging
from django.conf import settings
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

# Set up logging
logger = logging.getLogger(__name__)

def send_sms(to_number, message):
    """
    Send SMS using Twilio
    
    Args:
        to_number (str): Recipient's phone number (with country code, e.g., +91XXXXXXXXXX)
        message (str): SMS message content
    
    Returns:
        bool: True if sent successfully, False otherwise
    """
    try:
        # Check if Twilio credentials are configured
        if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
            error_msg = "Twilio credentials not configured. Please check your .env file"
            logger.error(error_msg)
            print(f"❌ {error_msg}")
            return False
        
        if not settings.TWILIO_PHONE_NUMBER:
            error_msg = "Twilio phone number not configured"
            logger.error(error_msg)
            print(f"❌ {error_msg}")
            return False
        
        # Check if in debug mode (print instead of send)
        if getattr(settings, 'SMS_DEBUG_MODE', False):
            print("\n" + "="*50)
            print("📱 SMS DEBUG MODE - Message not actually sent")
            print("="*50)
            print(f"TO: {to_number}")
            print(f"FROM: {settings.TWILIO_PHONE_NUMBER}")
            print(f"MESSAGE:\n{message}")
            print("="*50 + "\n")
            return True
        
        # Initialize Twilio client
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        
        # Send message
        message_obj = client.messages.create(
            body=message,
            from_=settings.TWILIO_PHONE_NUMBER,
            to=to_number
        )
        
        # Log success
        logger.info(f"SMS sent successfully to {to_number}")
        logger.info(f"Message SID: {message_obj.sid}")
        logger.info(f"Message Status: {message_obj.status}")
        
        print(f"✅ SMS sent successfully to {to_number}")
        print(f"📨 Message SID: {message_obj.sid}")
        
        return True
        
    except TwilioRestException as e:
        # Twilio specific errors
        error_msg = f"Twilio API Error: {str(e)}"
        logger.error(error_msg)
        print(f"❌ {error_msg}")
        
        # Provide helpful error messages
        if "21211" in str(e):
            print("💡 Tip: Invalid phone number format. Use country code (e.g., +91 for India)")
        elif "20003" in str(e):
            print("💡 Tip: Authentication failed. Check your Account SID and Auth Token")
        elif "21610" in str(e):
            print("💡 Tip: Phone number not verified for trial account. Add it in Verified Caller IDs")
        
        return False
        
    except Exception as e:
        # General errors
        error_msg = f"Failed to send SMS: {str(e)}"
        logger.error(error_msg)
        print(f"❌ {error_msg}")
        return False


def send_token_sms(phone_number, token_number, patient_name, wait_time):
    """
    Send token confirmation SMS when patient gets a new token
    
    Args:
        phone_number (str): Patient's phone number
        token_number (str): Generated token number
        patient_name (str): Patient's full name
        wait_time (int): Estimated wait time in minutes
    
    Returns:
        bool: True if sent successfully
    """
    message = f"""🏥 SMART HOSPITAL QUEUE SYSTEM

Hello {patient_name}!

✅ Your token has been issued successfully
📋 Token Number: {token_number}
⏱️ Estimated Wait Time: {wait_time} minutes

📱 Track your queue status at:
http://127.0.0.1:8000/queue-status/

💡 You will receive another SMS when it's your turn.

Thank you for choosing Smart Hospital!"""

    return send_sms(phone_number, message)


def send_reminder_sms(phone_number, token_number, position):
    """
    Send reminder SMS when patient is near their turn (position 3 or less)
    
    Args:
        phone_number (str): Patient's phone number
        token_number (str): Token number
        position (int): Current position in queue (1-3)
    
    Returns:
        bool: True if sent successfully
    """
    if position == 1:
        message = f"""🔔 SMART HOSPITAL REMINDER

Your token {token_number} is NEXT in queue!

Please be ready at the waiting area.
You will receive another SMS when it's your turn.

Thank you for your patience!"""
    elif position == 2:
        message = f"""🔔 SMART HOSPITAL REMINDER

Your token {token_number} is #2 in queue.

Please stay nearby as your turn is coming up soon.
Thank you!"""
    elif position == 3:
        message = f"""🔔 SMART HOSPITAL REMINDER

Your token {token_number} is #3 in queue.

Please be ready. You have approximately 10-15 minutes.
Thank you for waiting!"""
    else:
        return False  # Only send reminders for positions 1-3
    
    return send_sms(phone_number, message)


def send_ready_sms(phone_number, token_number, department_name):
    """
    Send SMS when patient's turn arrives
    
    Args:
        phone_number (str): Patient's phone number
        token_number (str): Token number
        department_name (str): Department name
    
    Returns:
        bool: True if sent successfully
    """
    message = f"""✅ SMART HOSPITAL ALERT

Token {token_number} is NOW READY!

📍 Please proceed to {department_name} department immediately
📋 Please bring your token number
👨‍⚕️ Doctor is ready to see you

Please report within 5 minutes.

Thank you for choosing Smart Hospital!"""

    return send_sms(phone_number, message)


def send_cancelled_sms(phone_number, token_number):
    """
    Send SMS when token is cancelled
    
    Args:
        phone_number (str): Patient's phone number
        token_number (str): Token number
    
    Returns:
        bool: True if sent successfully
    """
    message = f"""❌ SMART HOSPITAL NOTIFICATION

Your token {token_number} has been cancelled.

📞 Please contact reception for assistance:
• Reschedule your appointment
• Get a new token
• Speak with customer service

We apologize for any inconvenience caused.

Thank you for your understanding."""

    return send_sms(phone_number, message)


def send_completed_sms(phone_number, patient_name, department_name):
    """
    Send thank you SMS after consultation completion
    
    Args:
        phone_number (str): Patient's phone number
        patient_name (str): Patient's name
        department_name (str): Department name
    
    Returns:
        bool: True if sent successfully
    """
    message = f"""🏥 SMART HOSPITAL

Thank you {patient_name} for visiting {department_name} department.

✅ Your consultation is complete.
⭐ We hope you had a good experience.

📝 Please provide your feedback:
http://127.0.0.1:8000/feedback/

Take care and stay healthy! 💪"""

    return send_sms(phone_number, message)


def send_welcome_sms(phone_number, patient_name):
    """
    Send welcome SMS to new patient (optional)
    
    Args:
        phone_number (str): Patient's phone number
        patient_name (str): Patient's name
    
    Returns:
        bool: True if sent successfully
    """
    message = f"""🏥 Welcome to Smart Hospital, {patient_name}!

🌟 We're committed to providing you with:
• Minimal waiting time
• Quality healthcare
• Digital queue management

📱 Use our online portal to:
• Get digital tokens
• Track queue status
• Receive SMS alerts

Thank you for choosing us!"""

    return send_sms(phone_number, message)


def send_bulk_sms(phone_numbers, message):
    """
    Send SMS to multiple recipients
    
    Args:
        phone_numbers (list): List of phone numbers
        message (str): SMS message content
    
    Returns:
        dict: Success/failure counts
    """
    results = {
        'success': 0,
        'failed': 0,
        'failed_numbers': []
    }
    
    for number in phone_numbers:
        if send_sms(number, message):
            results['success'] += 1
        else:
            results['failed'] += 1
            results['failed_numbers'].append(number)
    
    print(f"\n📊 Bulk SMS Summary:")
    print(f"✅ Success: {results['success']}")
    print(f"❌ Failed: {results['failed']}")
    
    return results


# For testing purposes
if __name__ == "__main__":
    # Test the SMS functions
    print("Testing SMS Module...")
    print("="*50)
    
    # Example test (will only print in debug mode)
    test_number = "+9779765547826"  # Replace with your number for testing
    test_name = "Test Patient"
    test_token = "TEST-0001"
    test_wait = 15
    
    # Uncomment to test (only in debug mode)
    # send_token_sms(test_number, test_token, test_name, test_wait)
    # send_ready_sms(test_number, test_token, "Cardiology")
    # send_cancelled_sms(test_number, test_token)
    
    print("SMS Module loaded successfully!")
    print("To test SMS, set SMS_DEBUG_MODE=False in .env")
    print("and uncomment the test calls above.")