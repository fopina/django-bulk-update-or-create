import time

from django.core.management.base import BaseCommand
from django.db import transaction

import database_locks


class Command(BaseCommand):
    help = 'Lock it!'

    def add_arguments(self, parser):
        parser.add_argument('lock_name', help='lock name to be used')
        parser.add_argument(
            '-o',
            '--owner',
            help='Owner to be registered with the lock (used to renew and persist lock - hostname is default)',
        )
        parser.add_argument(
            '-d', '--duration', default=10, help='Lock duration (in seconds)'
        )

    def handle(self, *args, **options):
        with database_locks.lock(options['lock_name'], locked_by=options['owner']):
            self.stdout.write(f'Got the lock, sleeping {options["duration"]} seconds')
            time.sleep(options["duration"])
            self.stdout.write(f'Releasing lock')
