from django.db import models

class Server(models.Model):
    # Core server connection info
    ip_address = models.GenericIPAddressField()
    port = models.PositiveIntegerField()
    players = models.PositiveIntegerField(default=0)

    # Server descriptive info
    name = models.CharField(max_length=255)
    world = models.CharField(max_length=255, blank=True, null=True)
    rules = models.TextField(blank=True, null=True)
    version = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.ip_address}:{self.port})"
