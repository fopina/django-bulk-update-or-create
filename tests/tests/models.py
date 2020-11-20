from django.db import models
from bulk_update_or_create import BulkUpdateOrCreateQuerySet


class RandomData(models.Model):
    objects = BulkUpdateOrCreateQuerySet.as_manager()

    uuid = models.IntegerField(unique=True)
    value = models.IntegerField(default=0)
    data = models.CharField(max_length=200, null=True, blank=True)

    def __str__(self):
        return f'{self.uuid} - {self.data} - {self.value}'
