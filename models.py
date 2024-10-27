from django.db import models

class Server(models.Model):
    ip_address = models.GenericIPAddressField()
    port = models.PositiveIntegerField()
    players = models.PositiveIntegerField(default=0)
    name = models.CharField(max_length=255)
    world = models.CharField(max_length=255, blank=True, null=True)
    rules = models.TextField(blank=True, null=True)
    version = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.ip_address}:{self.port})"

class FetchLog(models.Model):
    last_fetched = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Last fetched at {self.last_fetched}"

    class Meta:
        verbose_name = "Fetch Log"
        verbose_name_plural = "Fetch Log Entries"

class RefreshInterval(models.Model):
    interval_minutes = models.PositiveIntegerField(default=30, help_text="Interval in minutes for data refresh")

    def __str__(self):
        return f"{self.interval_minutes} minutes"
