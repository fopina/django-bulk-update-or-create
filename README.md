# django-bulk-update-or-create


.. image:: https://github.com/fopina/django-database-locks/workflows/tests/badge.svg
    :target: https://github.com/fopina/django-database-locks/actions?query=workflow%3Atests
    :alt: tests

.. image:: https://codecov.io/gh/fopina/django-database-locks/branch/master/graph/badge.svg
   :target: https://codecov.io/gh/fopina/django-database-locks
   :alt: Test coverage status

.. image:: https://img.shields.io/pypi/v/django-database-locks
    :target: https://pypi.org/project/django-database-locks/
    :alt: Current version on PyPi

.. image:: https://img.shields.io/pypi/dm/django-database-locks
    :target: https://pypi.org/project/django-database-locks/
    :alt: monthly downloads

.. image:: https://img.shields.io/pypi/pyversions/django-database-locks
    :alt: PyPI - Python Version

.. image:: https://img.shields.io/pypi/djversions/django-database-locks
    :alt: PyPI - Django Version

Distributed locks for Django using DB (MySQL/Postgres)

Given the limitation that Percona Cluster does not support MySQL locks, this app implements locks using `select_for_update()` (row locks).

Installation
------------

    pip install django-database-locks


Usage
-----

`django-database-locks` exposes one single the `lock` contextmanager and the `locked` decorator.

The `locked` decorator will wrap a django management command (subclasses of `django.core.management.base.BaseCommand`) or any function with the `lock` contextmanager:


.. code-block:: python

    from django.core.management.base import BaseCommand

    from database_locks import locked

    @locked
    class Command(BaseCommand):
        ...
        def handle(self, *args, **options):
            self.stdout.write('Got the lock')


.. code-block:: python

    from database_locks import locked
    
    class SomeClass:
      def non_locked(self):
        pass
      
      @locked
      def locked(self):
        print('got lock')

.. code-block:: python

    from database_locks import lock
    
    class SomeClass:
      def non_locked(self):
        pass
      
      def locked(self):
        with lock():
            print('got lock')

Docs
----

Both `lock` and `locked` have the same optional args:

.. code-block:: python

    :param lock_name: unique name in DB for this function
    :param timeout: numbers of seconds to wait to acquire lock
    :param lock_ttl: expiration timer of the lock, in seconds (set to None to infinite)
    :param locked_by: owner id for the lock (if lock is active but owner is the same, returns acquired)
    :param auto_renew: if set to True will re-acquire lock (for `lock_ttl` seconds) before `lock_ttl` is over.
                       auto_renew thread will raise KeyboardInterrupt on the main thread in case re-acquiring fails
    :param retry: retry every `retry` seconds acquiring until successful. set to None or 0 to disable.
    :param lost_lock_cb: callback function when lock is lost (when re-acquiring). defaults to raising LockException

There are also the following options you can specify in the project `settings.py`

- *DATABASE_LOCKS_STATUS_FILE*: file that will be updated with the lock status (default `None`). Useful when you have multiple shared-lock processes, to quickly inspect which one has the lock.
- *DATABASE_LOCKS_ENABLED*: set to `False` to globally disable locks (default `True`)
