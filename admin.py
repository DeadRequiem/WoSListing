from django.contrib import admin
from .models import Server

@admin.register(Server)
class ServerAdmin(admin.ModelAdmin):
    list_display = ('name', 'ip_address', 'port', 'players', 'world', 'version')
    list_filter = ('world', 'version')
    search_fields = ('name', 'ip_address', 'world')
    ordering = ('name', 'ip_address')
