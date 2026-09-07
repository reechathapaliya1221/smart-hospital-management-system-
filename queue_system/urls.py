from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('get-token/', views.get_token, name='get_token'),
    path('queue-status/', views.queue_status, name='queue_status'),
    path('my-ticket/<int:token_id>/', views.my_ticket, name='my_ticket'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('api/queue-status/', views.api_queue_status, name='api_queue_status'),
]