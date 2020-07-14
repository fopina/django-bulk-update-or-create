from django.db import models


class BulkUpdateOrCreateMixin:
    def bulk_update_or_create(
        self,
        objs,
        update_fields,
        match_field='pk',
        batch_size=None,
        case_insensitive_match=False,
    ):
        """

        :param objs: 
        :param match_field: 
        :param update_fields: 
        :param batch_size: 
        :param case_insensitive_match: 
        """

        if not objs:
            raise ValueError('no objects to update_or_create...')
        if not update_fields:
            raise ValueError('update_fields cannot be empty')

        # generators not supported (for now?), as bulk_update doesn't either
        objs = list(objs)
        if batch_size is None:
            batch_size = len(objs)

        # validate that all objects have the required fields
        for obj in objs:
            if not hasattr(obj, match_field):
                raise ValueError(
                    f'some object does not have the match_field {match_field}'
                )
            for _f in update_fields:
                if not hasattr(obj, _f):
                    raise ValueError(f'some object does not have the update_field {_f}')

        batches = (objs[i : i + batch_size] for i in range(0, len(objs), batch_size))

        if case_insensitive_match:

            def _cased_key(obj):
                k = getattr(obj, match_field)
                return k.lower() if hasattr(k, 'lower') else k

        else:

            def _cased_key(obj):  # no-op
                return getattr(obj, match_field)

        for batch in batches:
            obj_map = {_cased_key(obj): obj for obj in batch}

            # mass select for bulk_update on existing ones
            to_update = list(self.filter(**{match_field + '__in': obj_map.keys()}))
            for to_u in to_update:
                obj = obj_map[_cased_key(to_u)]
                for _f in update_fields:
                    setattr(to_u, _f, getattr(obj, _f))
                del obj_map[_cased_key(to_u)]
            self.bulk_update(to_update, update_fields)

            # .create on the remaining (bulk_create won't work on multi-table inheritance models...)
            for obj in obj_map.values():
                obj.save()


class BulkUpdateOrCreateQuerySet(BulkUpdateOrCreateMixin, models.QuerySet):
    pass
