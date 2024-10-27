from django.contrib import admin
from django.core.management import call_command
from .models import Server, FetchLog, RefreshInterval

# Define the action to refresh server data
@admin.action(description='Refresh Server Data Now')
def refresh_server_data(modeladmin, request, queryset):
    call_command('fetch_server_data')
    modeladmin.message_user(request, "Server data refreshed successfully.")

# Register the Server model with admin site and include the custom action
@admin.register(Server)
class ServerAdmin(admin.ModelAdmin):
    list_display = ('name', 'ip_address', 'port', 'players', 'world', 'version')
    list_filter = ('world', 'version')
    search_fields = ('name', 'ip_address', 'world')
    ordering = ('name', 'ip_address')
    actions = [refresh_server_data]

# Register additional models for logging and interval configuration
@admin.register(FetchLog)
class FetchLogAdmin(admin.ModelAdmin):
    readonly_fields = ('last_fetched',)
    list_display = ('last_fetched',)

@admin.register(RefreshInterval)
class RefreshIntervalAdmin(admin.ModelAdmin):
    list_display = ('interval_minutes',)
