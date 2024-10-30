from django.shortcuts import render
from django.http import JsonResponse
from django.core.management import call_command
from django.utils import timezone
from datetime import timedelta
from .models import Server, FetchLog, MasterServer

# Dictionary to track the last refresh time per user IP
last_refresh_time = {}

def server_list(request):
    # Fetch all active master servers and their associated servers
    master_servers = MasterServer.objects.filter(is_active=True).prefetch_related('servers')
    last_update = FetchLog.objects.first()
    return render(request, 'server_list.html', {
        'master_servers': master_servers,
        'last_update': last_update
    })

def refresh_server_data(request):
    cooldown_period = timedelta(minutes=10)
    last_log = FetchLog.objects.first()

    if last_log and timezone.now() - last_log.last_fetched < cooldown_period:
        return JsonResponse({"status": "error", "message": "Please wait before refreshing again."})

    # Call the fetch server data management command
    call_command('fetch_server_data')

    # Update the FetchLog entry with the current time
    if last_log:
        last_log.last_fetched = timezone.now()
        last_log.save()
    else:
        FetchLog.objects.create(last_fetched=timezone.now())

    return JsonResponse({"status": "success", "message": "Server data refreshed successfully."})
