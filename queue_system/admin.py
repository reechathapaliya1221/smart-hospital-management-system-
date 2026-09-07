from django.contrib import admin
from .models import Department, Token

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'average_consultation_time', 'is_active', 'get_waiting_count']
    list_editable = ['is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'code']
    
    def get_waiting_count(self, obj):
        return obj.get_waiting_count()
    get_waiting_count.short_description = 'Waiting'

@admin.register(Token)
class TokenAdmin(admin.ModelAdmin):
    list_display = ['token_number', 'patient_name', 'department', 'priority', 'status', 'get_position', 'created_at']
    list_filter = ['status', 'priority', 'department', 'created_at']
    search_fields = ['token_number', 'patient_name', 'patient_phone']
    readonly_fields = ['token_number', 'created_at']  # Removed 'updated_at'
    
    def get_position(self, obj):
        return obj.get_position()
    get_position.short_description = 'Position'