# test_sms_module.py
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hospital_queue.settings')
django.setup()

from queue_system.utils.sms import send_sms, send_token_sms

# Your verified phone number (for testing)
YOUR_NUMBER = "+9779765547826"  # Replace with your actual number

print("Testing SMS Module")
print("="*50)

# Test 1: Simple SMS
print("\n1. Testing simple SMS...")
result = send_sms(YOUR_NUMBER, "Hello! Are you fine Rabi")

# Test 2: Token SMS
print("\n2. Testing token SMS...")
result2 = send_token_sms(YOUR_NUMBER, "TEST-001", "Test Patient", 15)

print("\n" + "="*50)
print("Test Complete!")