from .__version__ import __version__

from .query import BulkUpdateOrCreateQuerySet, BulkUpdateOrCreateMixin

__all__ = ['BulkUpdateOrCreateQuerySet', 'BulkUpdateOrCreateMixin']


default_app_config = 'bulk_update_or_create.apps.BulkUpdateOrCreateConfig'
