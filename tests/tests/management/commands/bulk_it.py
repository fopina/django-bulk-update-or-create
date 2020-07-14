import time

from django.core.management.base import BaseCommand

from tests.models import RandomData


class Command(BaseCommand):
    help = 'Lock it!'

    def handle(self, *args, **options):
        RandomData.objects.all().delete()
