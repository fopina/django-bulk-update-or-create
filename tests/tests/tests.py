from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.test import TestCase

from tests.models import RandomData


class Test(TestCase):
    def test_all_create(self):
        items = [RandomData(uuid=i, data=i) for i in range(10)]
        # 1 select + 10 creates, all new
        with self.assertNumQueries(11):
            RandomData.objects.bulk_update_or_create(
                items, ['data'], match_field='uuid'
            )
        self.assertEqual(RandomData.objects.count(), 10)
        self.assertEqual(
            sorted(int(x.data) for x in RandomData.objects.all()), list(range(10))
        )

    def test_update_some(self):
        self.test_all_create()
        items = [RandomData(uuid=i + 5, data=i + 10) for i in range(10)]
        # 1 select, 1 bulk update, 5 create
        with self.assertNumQueries(7):
            RandomData.objects.bulk_update_or_create(
                items, ['data'], match_field='uuid'
            )
        self.assertEqual(RandomData.objects.count(), 15)
        self.assertEqual(
            sorted(int(x.data) for x in RandomData.objects.all()),
            list(range(5)) + list(range(10, 20)),
        )

    def test_all_update(self):
        self.test_all_create()
        items = [RandomData(uuid=i, data=i + 10) for i in range(10)]
        # 1 select, 1 bulk update
        with self.assertNumQueries(2):
            RandomData.objects.bulk_update_or_create(
                items, ['data'], match_field='uuid'
            )
        self.assertEqual(RandomData.objects.count(), 10)
        self.assertEqual(
            sorted(int(x.data) for x in RandomData.objects.all()), list(range(10, 20)),
        )

    def test_update_some_generator(self):
        self.test_all_create()
        items = [RandomData(uuid=i + 5, data=i + 10) for i in range(10)]
        updated_items = RandomData.objects.bulk_update_or_create(
            items, ['data'], match_field='uuid', yield_objects=True
        )
        # not executed yet, just generator
        self.assertEqual(RandomData.objects.count(), 10)
        updated_items = list(updated_items)
        self.assertEqual(RandomData.objects.count(), 15)
        self.assertEqual(
            sorted(int(x.data) for x in RandomData.objects.all()),
            list(range(5)) + list(range(10, 20)),
        )
        # one batch
        self.assertEqual(len(updated_items), 1)
        # tuple with (created, updated)
        self.assertEqual(len(updated_items[0]), 2)
        # 5 were created - 15 to 19
        self.assertEqual(len(updated_items[0][0]), 5)
        self.assertEqual(
            sorted(int(x.data) for x in updated_items[0][0]), list(range(15, 20)),
        )
        for x in updated_items[0][0]:
            self.assertIsNotNone(x.pk)
        # 5 were updated - 10 to 14 (from 5 to 9)
        self.assertEqual(len(updated_items[0][1]), 5)
        self.assertEqual(
            sorted(int(x.data) for x in updated_items[0][1]), list(range(10, 15)),
        )
        for x in updated_items[0][1]:
            self.assertIsNotNone(x.pk)

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

    def test_update_some_with_context_manager(self):
        self.test_all_create()
        with self.assertNumQueries(7):
            with RandomData.objects.bulk_update_or_create_context(
                ['data'], match_field='uuid', batch_size=500
            ) as bulkit:
                for i in range(10):
                    bulkit.queue(RandomData(uuid=i + 5, data=i + 10))
        self.assertEqual(RandomData.objects.count(), 15)
        self.assertEqual(
            sorted(int(x.data) for x in RandomData.objects.all()),
            list(range(5)) + list(range(10, 20)),
        )

        # smaller batch_size to test more than 1 batch and test status_cb
        cb_calls = []

        def _cb(x):
            # nothing created
            self.assertEqual(x[0], [])
            cb_calls.extend(x[1])

        # 4 all-update batches = 8 queries
        with self.assertNumQueries(8):
            with RandomData.objects.bulk_update_or_create_context(
                ['data'], match_field='uuid', batch_size=3, status_cb=_cb
            ) as bulkit:
                for i in range(10):
                    bulkit.queue(RandomData(uuid=i, data=i + 20))
        self.assertEqual(RandomData.objects.count(), 15)
        self.assertEqual(
            # 20 to 29 ... 15 to 19
            sorted(int(x.data) for x in RandomData.objects.all()),
            list(range(15, 30)),
        )
        self.assertEqual(len(cb_calls), 10)
        for i in range(10):
            self.assertEqual(cb_calls[i].uuid, i)
            self.assertEqual(cb_calls[i].data, i + 20)
