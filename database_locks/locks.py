import inspect
import logging
import threading
import platform
import os
import time
import signal
from contextlib import contextmanager
from functools import wraps

from django.conf import settings
from django import db
from django.apps import apps
from django.utils import timezone
from django.core.management.base import BaseCommand


logger = logging.getLogger(__name__)


@contextmanager
def lock(
    lock_name,
    timeout=0,
    lock_ttl=10,
    locked_by=None,
    auto_renew=True,
    retry=0.5,
    lost_lock_cb=None,
):
    """
    :param lock_name: unique name in DB for this function
    :param timeout: numbers of seconds to wait to acquire lock
    :param lock_ttl: expiration timer of the lock, in seconds (set to None to infinite)
    :param locked_by: owner id for the lock (if lock is active but owner is the same, returns acquired)
    :param auto_renew: if set to True will re-acquire lock (for `lock_ttl` seconds) before `lock_ttl` is over.
                       auto_renew thread will raise KeyboardInterrupt on the main thread in case re-acquiring fails
    :param retry: retry every `retry` seconds acquiring until successful. set to None or 0 to disable.
    :param lost_lock_cb: callback function when lock is lost (when re-acquiring). defaults to raising LockException
    :return:
    """
    # TODO migrate to contextlib.ContextDecorator once only py3 is used
    _status_file('0')

    if not settings.DATABASE_LOCKS_ENABLED:
        logger.warning(
            'database_locks currently disabled in settings, adjust DATABASE_LOCKS_ENABLED if not intended'
        )
        yield
        return

    if not db.connection.features.has_select_for_update:
        logger.error(
            'database_locks cannot be used with the current database engine as it does not support SELECT .. FOR UPDATE, '
            'proceed at your own risk'
        )
        yield
        return

    logger.info('acquiring lock %s' % lock_name)
    lock = DBLock(lock_name, locked_by=locked_by)

    _status_file('1')

    time_started = time.time()
    while True:
        if lock.acquire(lock_ttl=lock_ttl):
            break
        if not retry:
            raise LockException('failed to acquire lock')
        if 0 < timeout < time.time() - time_started:
            raise LockException('failed to acquire lock within timeout', timeout)
        time.sleep(retry)

    # set SIGUSR1 handler for lost lock exception
    signal.signal(signal.SIGUSR1, lost_lock_cb or __default_lost_lock_cb)

    renew_thread = None
    if auto_renew:
        renew_thread = RenewThread(lock, lock_ttl)
        renew_thread.start()

    _status_file('2')
    yield

    if renew_thread:
        renew_thread.stop()
    lock.release()


def locked(func_or_name=None, **lock_kwargs):
    """
    Decorator to apply the `lock()` context manager to a function or class

    :param func_or_name: decorated function/class - used as lock name
    :param lock_kwargs: passed directly to `lock()`, refer to its documentation
    :return: decorated function/class
    """

    def decorator(func):
        if func_or_name and func_or_name != func:
            name = func_or_name
        else:
            # TODO classes inside the same module with same function names will get same default name...
            name = '{}.{}'.format(func.__module__, func.__name__)

        if inspect.isclass(func):
            if not issubclass(func, BaseCommand):
                raise NotImplementedError(
                    'only django BaseCommand subclasses are supported for now'
                )

            orig_handle = func.handle

            @wraps(func.handle)
            def new_handle(self, *args, **kwargs):
                with lock(name, **lock_kwargs):
                    return orig_handle(self, *args, **kwargs)

            func.handle = new_handle

            return func
        else:

            @wraps(func)
            def wrapper(*args, **kwds):
                with lock(name, **lock_kwargs):
                    return func(*args, **kwds)

            return wrapper

    if func_or_name and callable(func_or_name):
        return decorator(func_or_name)
    return decorator


class DBLock:
    def __init__(self, name, locked_by=None):
        self._name = name
        if locked_by is None:
            self._locked_by = f'{platform.node()}.{os.getpid()}'
        else:
            self._locked_by = locked_by
        # delay import model as class decorator runs before apps are ready
        self._model = apps.get_model('database_locks', 'Lock')
        self.__last_owner = None

    @property
    def name(self):
        # read-only (wrapper ofc, it's python...)
        return self._name

    def acquire(self, lock_ttl=10):
        with db.transaction.atomic():
            dblock = (
                self._model.objects.select_for_update().filter(name=self._name).first()
            )
            if dblock is None:
                logger.debug(
                    'lock %s not yet created, trying to create (and acquire)',
                    self._name,
                )
                # not protected by select_for_update so let's use just `.create`
                # so it blows up with IntegrityError in case of race (as name is unique)
                try:
                    self._model.objects.create(
                        name=self._name,
                        locked_by=self._locked_by,
                        expires_at=timezone.now()
                        + timezone.timedelta(seconds=lock_ttl),
                    )
                    logger.debug('lock %s (created and) acquired', self._name)
                    return True
                except db.IntegrityError:
                    logger.debug('could not create lock %s, try next time', self._name)
                    return False
            if dblock.active and dblock.locked_by != self._locked_by:
                # it's DEBUG level but no need to spam...
                if dblock.locked_by != self.__last_owner:
                    logger.debug(
                        'lock %s active and owned by %s, try later',
                        self._name,
                        dblock.locked_by,
                    )
                    self.__last_owner = dblock.locked_by
                return False

            dblock.locked_by = self._locked_by
            dblock.expires_at = timezone.now() + timezone.timedelta(seconds=lock_ttl)
            dblock.save()
            logger.debug('lock %s acquired/renewed', self._name)
            return True

    def release(self):
        logger.debug('releasing lock %s', self._name)
        with db.transaction.atomic():
            dblock = (
                self._model.objects.select_for_update().filter(name=self._name).first()
            )
            if dblock and dblock.active and dblock.locked_by == self._locked_by:
                dblock.expires_at = None
                dblock.save()
                logger.debug('released lock %s', self._name)


class RenewThread(threading.Thread):
    EARLY_TICK = 1

    def __init__(self, lock_obj, ttl):
        super(RenewThread, self).__init__()

        self.__lock = lock_obj
        self.__ttl = ttl
        # renew 1 second before TTL
        self.__wait = max(ttl - self.EARLY_TICK, 1)

        self.__stopped = threading.Event()
        self.daemon = True

    def renew(self):
        # is there any other way to notify main thread?
        try:
            if self.__lock.acquire(lock_ttl=self.__ttl):
                return
            logger.error('failed to re-acquire lock %s', self.__lock.name)
        except Exception:
            # any exception happens, treat it as failed to acquire...
            logger.exception('some error re-acquiring lock %s', self.__lock.name)

        # not really needed, but doesn't hurt
        self.__stopped.set()
        os.kill(os.getpid(), signal.SIGUSR1)

    def run(self):
        while True:
            self.renew()
            if self.__stopped.wait(self.__wait):
                break

    def stop(self):
        self.__stopped.set()
        return self.__stopped.wait()


class LockException(Exception):
    pass


def __default_lost_lock_cb(*_):
    raise LockException('lost lock, terminating')


def _status_file(message):
    if settings.DATABASE_LOCKS_STATUS_FILE is None:
        return
    try:
        with open(settings.DATABASE_LOCKS_STATUS_FILE, 'w') as _f:
            _f.write(message)
    except Exception:
        # log but don't break anything
        logger.exception(
            'failed to update lock status file %s', settings.DATABASE_LOCKS_STATUS_FILE
        )

