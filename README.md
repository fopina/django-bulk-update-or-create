# django-bulk-update-or-create


[![tests](https://github.com/fopina/django-bulk-update-or-create/workflows/tests/badge.svg)](https://github.com/fopina/django-bulk-update-or-create/actions?query=workflow%3Atests)
[![Test coverage status](https://codecov.io/gh/fopina/django-bulk-update-or-create/branch/master/graph/badge.svg)](https://codecov.io/gh/fopina/django-bulk-update-or-create)
[![Current version on PyPi](https://img.shields.io/pypi/v/django-bulk-update-or-create)](https://pypi.org/project/django-bulk-update-or-create/)
[![monthly downloads](https://img.shields.io/pypi/dm/django-bulk-update-or-create)](https://pypi.org/project/django-bulk-update-or-create/)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/django-bulk-update-or-create)
![PyPI - Django Version](https://img.shields.io/pypi/djversions/django-bulk-update-or-create)


Everyone using Django ORM will eventually find himself doing batch `update_or_create` operations: ingest files from external sources, sync with external APIs, etc.

If the number of records is big, the slowliness of `QuerySet.update_or_create` will stand out: it is very practical to use but it always does one `SELECT` and then one `INSERT` (if select didn't return anything) or `UPDATE`/`.save` (if it did).

Searching online shows that this does indeed happen to quite a few people though it doesn't seem to be any good solution:

* `bulk_create` is really fast if you know all records are new (and you're not using multi-table inheritance)
* `bulk_update` does some nice voodoo to update several records with the same `UPDATE` statement (using a huge `WHERE` condition together with `CASE`), but you need to be sure they all exist
* UPSERTs [(INSERT .. ON DUPLICATE KEY UPDATE](https://dev.mysql.com/doc/refman/8.0/en/insert-on-duplicate.html)) look interesting (TODO on different package) but they will be retricted by `bulk_create` limitations ==> cannot use on models with multi-table inheritance

This package tries to tackle this introducnig `bulk_update_or_create` to model QuerySet/Manager:
* `update_or_create`: `(1 SELECT + 1 INSERT/UPDATE) * N`
* `bulk_update_or_create`: `1 BIG_SELECT + 1 BIG_UPDATE + (lte_N) INSERT`

For a batch of records:

* `SELECT` all from database (based on the `match_field` parameter)
* Update records in memory
* Use `bulk_update` for those
* Use `INSERT`/`.create` on each of the remaining

The (*SOFTCORE*) [performance test](tests/tests/management/commands/bulk_it.py) looks promising, more than 70% less time (average):

```shell
$ make testcmd
# default - sqlite
DJANGO_SETTINGS_MODULE=settings tests/manage.py bulk_it
loop of update_or_create - all creates: 3.966486692428589
loop of update_or_create - all updates: 4.020653247833252
loop of update_or_create - half half: 3.9968857765197754
bulk_update_or_create - all creates: 2.949239730834961
bulk_update_or_create - all updates: 0.15633511543273926
bulk_update_or_create - half half: 1.4585723876953125
# mysql
DJANGO_SETTINGS_MODULE=settings_mysql tests/manage.py bulk_it
loop of update_or_create - all creates: 5.511938571929932
loop of update_or_create - all updates: 5.321666955947876
loop of update_or_create - half half: 5.391834735870361
bulk_update_or_create - all creates: 1.5671980381011963
bulk_update_or_create - all updates: 0.14612770080566406
bulk_update_or_create - half half: 0.7262606620788574
# postgres
DJANGO_SETTINGS_MODULE=settings_postgresql tests/manage.py bulk_it
loop of update_or_create - all creates: 4.3584535121917725
loop of update_or_create - all updates: 3.6183276176452637
loop of update_or_create - half half: 4.145816087722778
bulk_update_or_create - all creates: 1.044851541519165
bulk_update_or_create - all updates: 0.14954638481140137
bulk_update_or_create - half half: 0.8407495021820068
```

Installation
============

```
pip install django-bulk-update-or-create
```

Add it to your `INSTALLED_APPS` list in `settings.py`

Usage
=====

* use `BulkUpdateOrCreateQuerySet` as manager of your model(s)

```python
from django.db import models
from bulk_update_or_create import BulkUpdateOrCreateQuerySet


class RandomData(models.Model):
    objects = BulkUpdateOrCreateQuerySet.as_manager()

    uuid = models.IntegerField(unique=True)
    data = models.CharField(max_length=200, null=True, blank=True)
```

* call `bulk_update_or_create`

```python
items = [
    RandomData(uuid=1, data='data for 1'),
    RandomData(uuid=2, data='data for 2'),
]
RandomData.objects.bulk_update_or_create(items, ['data'], match_field='uuid')
```

* or use the context manager, if you are updating a big number of items, as it manages a batch queue

```python
with RandomData.objects.bulk_update_or_create_context(['data'], match_field='uuid', batch_size=10) as bulkit:
    for i in range(10000):
        bulkit.queue(RandomData(uuid=i, data=i + 20))
```

`bulk_update_or_create` supports `yield_objects=True` so you can iterate over the created/updated objects.  
`bulk_update_or_create_context` provides the same information to the callback function specified as `status_cb`

Docs
====

WIP

ToDo
====

* [ ]  Docs!
* [ ]  Add option to use `bulk_create` for creates: assert model is not multi-table, if enabled
* [ ]  Fix the collation mess: the keyword arg `case_insensitive_match` should be dropped and collation detected in runtime
* [ ]  Add support for multiple `match_field` - probably will need to use `WHERE (K1=X and K2=Y) or (K1=.. and K2=..)` instead of `IN` for those, as that SQL standard doesn't seem widely adopted yet
* [ ]  Link to `UPSERT` alternative package once done!
