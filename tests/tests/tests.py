from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.test import TestCase

from tests.models import RandomData


class Test(TestCase):
    def test_all_create(self):
        items = [RandomData(uuid=i, data=i) for i in range(10)]
        RandomData.objects.bulk_update_or_create(items, ['data'], match_field='uuid')
        self.assertEqual(RandomData.objects.count(), 10)
        self.assertEqual(
            sorted(int(x.data) for x in RandomData.objects.all()), list(range(10))
        )

    def test_update_some(self):
        self.test_all_create()
        items = [RandomData(uuid=i + 5, data=i + 10) for i in range(10)]
        RandomData.objects.bulk_update_or_create(items, ['data'], match_field='uuid')
        self.assertEqual(RandomData.objects.count(), 15)
        self.assertEqual(
            sorted(int(x.data) for x in RandomData.objects.all()),
            list(range(5)) + list(range(10, 20)),
        )

    def test_errors(self):
        with self.assertRaises(ValueError) as cm:
            RandomData.objects.bulk_update_or_create([], [])
        self.assertEqual(cm.exception.args, ('no objects to update_or_create...',))
        with self.assertRaises(ValueError) as cm:
            RandomData.objects.bulk_update_or_create([None], [])
        self.assertEqual(cm.exception.args, ('update_fields cannot be empty',))

        with self.assertRaises(ValueError) as cm:
            RandomData.objects.bulk_update_or_create(
                [RandomData(uuid=1, data='x')], ['data'], match_field='x'
            )
        self.assertEqual(
            cm.exception.args, ('some object does not have the match_field x',)
        )
        with self.assertRaises(ValueError) as cm:
            RandomData.objects.bulk_update_or_create(
                [RandomData(uuid=1, data='x')], ['x'], match_field='uuid'
            )
        self.assertEqual(
            cm.exception.args, ('some object does not have the update_field x',)
        )

    def test_case_sensitivity(self):
        """
        match_fields should always be unique but for test simplicity (no extra model),
        using RandomData.data
        """
        RandomData.objects.bulk_update_or_create(
            [RandomData(uuid=1, data='x'),], ['uuid'], match_field='data'
        )
        self.assertEqual(RandomData.objects.count(), 1)
        self.assertEqual(sorted(x.data for x in RandomData.objects.all()), ['x'])

        RandomData.objects.bulk_update_or_create(
            [RandomData(uuid=2, data='X'),],
            ['uuid'],
            match_field='data',
            case_insensitive_match=True,
        )
        self.assertEqual(RandomData.objects.count(), 1)
        self.assertEqual(sorted(x.data for x in RandomData.objects.all()), ['x'])

        RandomData.objects.bulk_update_or_create(
            [RandomData(uuid=3, data='X'),], ['uuid'], match_field='data',
        )
        self.assertEqual(RandomData.objects.count(), 2)
        self.assertEqual(sorted(x.data for x in RandomData.objects.all()), ['X', 'x'])
