from django.db import models


class BulkUpdateOrCreateMixin:
    def bulk_update_or_create(
        self,
        objs,
        update_fields,
        match_field='pk',
        batch_size=None,
        case_insensitive_match=False,
        yield_objects=False,
    ):
        """

        :param objs: model instances to be updated or created
        :param update_fields: fields that will be updated if record already exists (passed on to bulk_update)
        :param match_field: model field that will match existing records (defaults to "pk")
        :param batch_size: number of records to process in each batch (defaults to len(objs))
        :param case_insensitive_match: set to True if using MySQL with "ci" collations (defaults to False)
        :param yield_objects: if True, method becomes a generator that will yield a tuple of lists with ([created], [updated]) objects
        """

        r = self.__bulk_update_or_create(
            objs,
            update_fields,
            match_field,
            batch_size,
            case_insensitive_match,
            yield_objects,
        )
        if yield_objects:
            return r
        return list(r)

    def __bulk_update_or_create(
        self,
        objs,
        update_fields,
        match_field='pk',
        batch_size=None,
        case_insensitive_match=False,
        yield_objects=False,
    ):
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
            created_objs = []
            for obj in obj_map.values():
                obj.save()
                created_objs.append(obj)
            if yield_objects:
                yield created_objs, to_update


class BulkUpdateOrCreateQuerySet(BulkUpdateOrCreateMixin, models.QuerySet):
    pass
