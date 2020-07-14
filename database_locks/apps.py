from django.apps import AppConfig
from django.conf import settings

APP_SETTINGS = dict(STATUS_FILE=None, ENABLED=True)


class DBLocksConfig(AppConfig):
    name = 'database_locks'

    def ready(self):
        for k, v in APP_SETTINGS.items():
            _k = 'DATABASE_LOCKS_%s' % k
            if not hasattr(settings, _k):
                setattr(settings, _k, v)
