from time import time

from django.core.management.base import BaseCommand

from tests.models import RandomData
from contextlib import contextmanager


@contextmanager
def timing(description: str) -> None:
    start = time()
    yield
    ellapsed_time = time() - start

    print(f"{description}: {ellapsed_time}")


class Command(BaseCommand):
    help = 'Lock it!'

    def _loop(self, n=1000, offset=0, data_offset=0):
        for i in range(n):
            RandomData.objects.update_or_create(
                uuid=i + offset, defaults={'data': str(i + offset + data_offset)},
            )

    def _bulk(self, n=1000, offset=0, data_offset=0):
        items = [
            RandomData(uuid=i + offset, data=str(i + offset + data_offset))
            for i in range(n)
        ]
        RandomData.objects.bulk_update_or_create(items, ['data'], match_field='uuid')

    def _clear(self):
        RandomData.objects.all().delete()

    def _check(self, n=1000, min=0, max=999):
        values = sorted([int(x.data) for x in RandomData.objects.all()])
        assert len(values) == n
        assert values[0] == min
        assert values[-1] == max

    def handle(self, *args, **options):
        self._clear()

        with timing('loop of update_or_create - all creates'):
            self._loop()
        self._check()

        with timing('loop of update_or_create - all updates'):
            self._loop(data_offset=1)
        self._check(1000, 1, 1000)

        with timing('loop of update_or_create - half half'):
            self._loop(offset=500, data_offset=2)
        self._check(1500, 1, 1501)

        self._clear()

        with timing('bulk_update_or_create - all creates'):
            self._bulk()
        self._check()

        with timing('bulk_update_or_create - all updates'):
            self._bulk(data_offset=1)
        self._check(1000, 1, 1000)

        with timing('bulk_update_or_create - half half'):
            self._bulk(offset=500, data_offset=2)
        self._check(1500, 1, 1501)
