from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard_home, name='home'),
    path('settings/', views.settings_view, name='settings'),
    path('proxies/', views.proxy_management, name='proxies'),
    path('control/', views.bot_control, name='control'),
    path('session/<str:session_id>/', views.session_detail, name='session_detail'),
    path('api/session/<str:session_id>/', views.api_session_data, name='api_session_data'),
    path('logs/', views.logs_view, name='logs'),
    path('api/update-viewer-stats/', views.api_update_viewer_stats, name='api_update_viewer_stats'),
    path('api/fetch-free-proxies/', views.api_fetch_free_proxies, name='api_fetch_free_proxies'),
    path('api/load-free-proxies/', views.api_load_free_proxies, name='api_load_free_proxies'),
    path('api/autofetch-settings/', views.api_get_autofetch_settings, name='api_get_autofetch_settings'),
    path('api/autofetch-settings/save/', views.api_save_autofetch_settings, name='api_save_autofetch_settings'),
    path('api/logs/', views.api_get_logs, name='api_get_logs'),
]