from django.db import models

class MasterServer(models.Model):
    name = models.CharField(max_length=100, help_text="Descriptive name for the master server")
    ip_address = models.GenericIPAddressField()
    port = models.PositiveIntegerField()
    is_active = models.BooleanField(default=True, help_text="Toggle to enable or disable this master server")
    priority = models.PositiveIntegerField(default=1, help_text="Lower values have higher priority in fetch order")

    def __str__(self):
        return f"{self.name} ({self.ip_address}:{self.port}) - Priority {self.priority}"

class Server(models.Model):
    ip_address = models.GenericIPAddressField()
    port = models.PositiveIntegerField()
    players = models.PositiveIntegerField(default=0)
    name = models.CharField(max_length=255)
    world = models.CharField(max_length=255, blank=True, null=True)
    rules = models.TextField(blank=True, null=True)
    version = models.CharField(max_length=50, blank=True, null=True)
    server_type = models.CharField(
        max_length=20,
        choices=[('Mix', 'Mix'), ('ReMix', 'ReMix')],
        default='Mix',
        help_text="Indicates whether the server is a Mix or ReMix server"
    )
    master_server = models.ForeignKey(
        MasterServer,
        on_delete=models.CASCADE,
        related_name='servers',
        null=True,
        blank=True,
        help_text="The master server from which this server was fetched"
    )

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
