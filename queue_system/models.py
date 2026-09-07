from django.db import models

class Department(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10, unique=True)
    average_consultation_time = models.IntegerField(default=15)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name
    
    def get_waiting_count(self):
        return Token.objects.filter(department=self, status='waiting').count()

class Token(models.Model):
    STATUS_CHOICES = [
        ('waiting', 'Waiting'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    PRIORITY_CHOICES = [
        ('normal', 'Normal'),
        ('urgent', 'Urgent'),
        ('emergency', 'Emergency'),
    ]
    
    token_number = models.CharField(max_length=20, blank=True)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    patient_name = models.CharField(max_length=100)
    patient_phone = models.CharField(max_length=15)
    patient_email = models.EmailField(blank=True)
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='normal')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='waiting')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)  # Add this line
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    predicted_wait_time = models.IntegerField(default=0)
    actual_wait_time = models.IntegerField(null=True, blank=True)
    
    def save(self, *args, **kwargs):
        if not self.token_number:
            last_token = Token.objects.filter(department=self.department).order_by('-created_at').first()
            if last_token and last_token.token_number:
                try:
                    last_num = int(last_token.token_number.split('-')[-1])
                    self.token_number = f"{self.department.code}-{last_num + 1:04d}"
                except:
                    self.token_number = f"{self.department.code}-{1:04d}"
            else:
                self.token_number = f"{self.department.code}-{1:04d}"
        super().save(*args, **kwargs)
    
    def get_position(self):
        if self.status == 'waiting':
            return Token.objects.filter(
                department=self.department,
                status='waiting',
                created_at__lt=self.created_at
            ).count() + 1
        return 0
    
    def __str__(self):
        return f"{self.token_number} - {self.patient_name}"