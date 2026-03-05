from django.contrib import admin
from .models import BotConfiguration, Proxy, BotSession, Viewer


@admin.register(BotConfiguration)
class BotConfigurationAdmin(admin.ModelAdmin):
    list_display = ('id', 'live_url', 'num_viewers', 'created_by', 'created_at')
    list_filter = ('created_by', 'created_at')
    search_fields = ('live_url',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Proxy)
class ProxyAdmin(admin.ModelAdmin):
    list_display = ('proxy_url', 'is_active', 'last_used', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('proxy_url',)


@admin.register(BotSession)
class BotSessionAdmin(admin.ModelAdmin):
    list_display = ('session_id', 'status', 'viewers_count', 'success_count', 'start_time', 'end_time')
    list_filter = ('status', 'start_time')
    search_fields = ('session_id',)
    readonly_fields = ('start_time', 'end_time')


@admin.register(Viewer)
class ViewerAdmin(admin.ModelAdmin):
    list_display = ('viewer_id', 'session', 'status', 'comments_sent', 'reactions_made', 'start_time')
    list_filter = ('status', 'session', 'start_time')
    search_fields = ('viewer_id',)
    readonly_fields = ('start_time', 'end_time')