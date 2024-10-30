from django.contrib import admin
from django.core.management import call_command
from .models import Server, FetchLog, RefreshInterval, MasterServer

# Define the action to refresh server data
@admin.action(description='Refresh Server Data Now')
def refresh_server_data(modeladmin, request, queryset):
    call_command('fetch_server_data')
    modeladmin.message_user(request, "Server data refreshed successfully.")

# Register the Server model with admin site and include the custom action
@admin.register(Server)
class ServerAdmin(admin.ModelAdmin):
    list_display = ('name', 'ip_address', 'port', 'players', 'world', 'version', 'server_type')  # Added server_type
    list_filter = ('world', 'version', 'server_type')  # Added server_type to filter options
    search_fields = ('name', 'ip_address', 'world', 'server_type')  # Added server_type to search
    ordering = ('name', 'ip_address')
    actions = [refresh_server_data]

# Register FetchLog model with read-only last_fetched field
@admin.register(FetchLog)
class FetchLogAdmin(admin.ModelAdmin):
    readonly_fields = ('last_fetched',)
    list_display = ('last_fetched',)

# Register RefreshInterval model with interval_minutes display
@admin.register(RefreshInterval)
class RefreshIntervalAdmin(admin.ModelAdmin):
    list_display = ('interval_minutes',)

@admin.register(MasterServer)
class MasterServerAdmin(admin.ModelAdmin):
    list_display = ('name', 'ip_address', 'port', 'is_active', 'priority')
    list_filter = ('is_active',)
    search_fields = ('name', 'ip_address')
