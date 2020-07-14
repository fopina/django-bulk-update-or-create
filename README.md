# django-bulk-update-or-create


[![tests](https://github.com/fopina/django-database-locks/workflows/tests/badge.svg)](https://github.com/fopina/django-database-locks/actions?query=workflow%3Atests)

[![Test coverage status](https://codecov.io/gh/fopina/django-database-locks/branch/master/graph/badge.svg)](https://codecov.io/gh/fopina/django-database-locks)

[![Current version on PyPi](https://img.shields.io/pypi/v/django-database-locks)](https://pypi.org/project/django-database-locks/)

[![monthly downloads](https://img.shields.io/pypi/dm/django-database-locks)](https://pypi.org/project/django-database-locks/)

![PyPI - Python Version](https://img.shields.io/pypi/pyversions/django-database-locks)

![PyPI - Django Version](https://img.shields.io/pypi/djversions/django-database-locks)

Distributed locks for Django using DB (MySQL/Postgres)

Given the limitation that Percona Cluster does not support MySQL locks,
this app implements locks using `select_for_update()` (row
locks).

Installation
============

> pip install django-database-locks

Usage
=====


```python
from django.core.management.base import BaseCommand

from database_locks import locked

@locked
class Command(BaseCommand):
    ...
    def handle(self, *args, **options):
        self.stdout.write('Got the lock')
```

Docs
====

Both [lock]{.title-ref} and [locked]{.title-ref} have the same optional
args:

```python
:param lock_name: unique name in DB for this function
:param timeout: numbers of seconds to wait to acquire lock
:param lock_ttl: expiration timer of the lock, in seconds (set to None to infinite)
:param locked_by: owner id for the lock (if lock is active but owner is the same, returns acquired)
:param auto_renew: if set to True will re-acquire lock (for `lock_ttl` seconds) before `lock_ttl` is over.
                   auto_renew thread will raise KeyboardInterrupt on the main thread in case re-acquiring fails
:param retry: retry every `retry` seconds acquiring until successful. set to None or 0 to disable.
:param lost_lock_cb: callback function when lock is lost (when re-acquiring). defaults to raising LockException
```
