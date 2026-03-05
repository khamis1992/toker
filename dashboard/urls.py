from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard_home, name='home'),
    path('settings/', views.settings_view, name='settings'),
    path('proxies/', views.proxy_management, name='proxies'),
    path('control/', views.bot_control, name='control'),
    path('session/<str:session_id>/', views.session_detail, name='session_detail'),
    path('logs/', views.logs_view, name='logs'),
    path('api/update-viewer-stats/', views.api_update_viewer_stats, name='api_update_viewer_stats'),
]