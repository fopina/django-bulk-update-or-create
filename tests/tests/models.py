from django.db import models


class RandomData(models.Model):
    uuid = models.IntegerField(unique=True)
    data = models.CharField(max_length=200, null=True, blank=True)
