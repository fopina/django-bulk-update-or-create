from django.db import models
from django.utils import timezone


class Lock(models.Model):
    name = models.CharField(max_length=255, unique=True)
    locked_by = models.TextField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    @property
    def active(self):
        return self.expires_at is not None and timezone.now() <= self.expires_at
