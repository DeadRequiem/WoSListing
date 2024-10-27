import time
from django.core.management.base import BaseCommand
from django.core.management import call_command
from ServerList.models import RefreshInterval
from datetime import datetime

# python manage.py scheduled_fetch --interval 3600

class Command(BaseCommand):
    help = "Periodically fetch server data at a specified interval"

    def add_arguments(self, parser):
        parser.add_argument(
            '--interval', type=int, default=3600,
            help='Interval in seconds between fetches if no admin setting (default: 3600 seconds = 1 hour)'
        )

    def handle(self, *args, **options):
        # Default interval from command-line argument if no interval is set in admin
        default_interval = options['interval']
        self.stdout.write(f"Starting scheduled fetch every {default_interval} seconds")

        while True:
            # Get the interval from RefreshInterval model, if available, else use default interval
            interval_obj = RefreshInterval.objects.first()
            interval_seconds = interval_obj.interval_minutes * 60 if interval_obj else default_interval

            # Log and execute the fetch command
            self.stdout.write(f"[{datetime.now()}] Fetching server data...")
            call_command('fetch_server_data')
            self.stdout.write(f"[{datetime.now()}] Fetch complete. Next fetch in {interval_seconds} seconds.")

            # Wait for the specified interval
            time.sleep(interval_seconds)
