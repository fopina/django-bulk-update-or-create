from django.db import models


class BulkUpdateOrCreateMixin:
    def bulk_update_or_create_context(
        self,
        update_fields,
        match_field='pk',
        batch_size=100,
        case_insensitive_match=False,
        status_cb=None,
    ):
        """
        Helper method that returns a context manager (_BulkUpdateOrCreateContextManager) that makes it easier to handle
        a stream of objects with unknown size.
        Call `.queue(obj)` and whenever `batch_size` is reached or the context terminates, this context manager will
        call `bulk_update_or_create` on the queue

        :param update_fields: fields that will be updated if record already exists (passed on to bulk_update)
        :param match_field: model field that will match existing records (defaults to "pk")
        :param batch_size: number of records to process in each batch (defaults to 100)
        :param case_insensitive_match: set to True if using MySQL with "ci" collations (defaults to False)
        :param status_cb: if set to a callable, status_cb is called a tuple of lists with ([created],
            [updated]) objects as they're yielded
        """
        return _BulkUpdateOrCreateContextManager(
            self,
            update_fields,
            batch_size=batch_size,
            status_cb=status_cb,
            match_field=match_field,
            case_insensitive_match=case_insensitive_match,
        )

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
        :param match_field: model fields that will match existing records (defaults to ["pk"])
        :param batch_size: number of records to process in each batch (defaults to len(objs))
        :param case_insensitive_match: set to True if using MySQL with "ci" collations (defaults to False)
        :param yield_objects: if True, method becomes a generator that will yield a tuple of lists
            with ([created], [updated]) objects
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

    def __bulk_update_or_create_inner_methods(self, match_fields, case_insensitive_match):
        single_match_field = len(match_fields) == 1

        def _obj_key_getter_sensitive(obj):
            # use to_python to coerce value same way it's done when fetched from DB
            # https://github.com/fopina/django-bulk-update-or-create/issues/11
            # k = _match_field.to_python(_match_field.value_from_object(obj))
            return tuple(match_field.to_python(match_field.value_from_object(obj)) for match_field in match_fields)

        _obj_key_getter = _obj_key_getter_sensitive

        if case_insensitive_match:

            def _obj_key_getter(obj):
                return tuple(
                    map(
                        lambda v: v.lower() if hasattr(v, 'lower') else v,
                        _obj_key_getter_sensitive(obj),
                    )
                )

        if single_match_field:

            def _obj_filter(obj_map):
                return models.Q(**{f'{match_fields[0].name}__in': obj_map.keys()})

            def _obj_key_getter_single(obj):
                return _obj_key_getter(obj)[0]

            return _obj_key_getter_single, _obj_filter
        else:

            def _obj_filter(obj_map):
                return models.Q(
                    *(
                        models.Q(**{k.name: obj_key[i] for i, k in enumerate(match_fields)})
                        for obj_key in obj_map.keys()
                    ),
                    _connector=models.Q.OR,
                )

            return _obj_key_getter, _obj_filter

    def __bulk_update_or_create(
        self,
        objs,
        update_fields,
        match_field='pk',
        batch_size=None,
        case_insensitive_match=False,
        yield_objects=False,
    ):
        # validations like bulk_update
        if batch_size is not None and batch_size < 0:
            raise ValueError('Batch size must be a positive integer.')
        if not update_fields:
            raise ValueError('update_fields cannot be empty')
        match_field = (match_field,) if isinstance(match_field, str) else match_field
        _match_fields = [self.model._meta.get_field(name) for name in match_field]
        _update_fields = [self.model._meta.get_field(name) for name in update_fields]
        if any(not f.concrete or f.many_to_many for f in _update_fields):
            raise ValueError('bulk_update_or_create() can only be used with concrete fields.')
        if any(f.primary_key for f in _update_fields):
            raise ValueError('bulk_update_or_create() cannot be used with primary key fields.')

        # generators not supported (for now?), as bulk_update doesn't either
        objs = list(objs)
        if not objs:
            return

        if batch_size is None:
            batch_size = len(objs)

        batches = (objs[i : i + batch_size] for i in range(0, len(objs), batch_size))

        _obj_key_getter, _obj_filter = self.__bulk_update_or_create_inner_methods(_match_fields, case_insensitive_match)

        for batch in batches:
            obj_map = {_obj_key_getter(obj): obj for obj in batch}

            # mass select for bulk_update on existing ones
            to_update = self.filter(_obj_filter(obj_map))

            for to_u in to_update:
                obj = obj_map[_obj_key_getter(to_u)]
                for _f in update_fields:
                    setattr(to_u, _f, getattr(obj, _f))
                del obj_map[_obj_key_getter(to_u)]
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


class _BulkUpdateOrCreateContextManager:
    def __init__(self, queryset, update_fields, batch_size=500, status_cb=None, **kwargs):
        self._queue = []
        self._queryset = queryset
        self._batch_size = batch_size
        assert status_cb is None or callable(status_cb)
        self._cb = status_cb
        self._fields = update_fields
        self._kwargs = kwargs

    def queue(self, obj):
        self._queue.append(obj)
        if len(self._queue) >= self._batch_size:
            self.dump_queue()

    def queue_obj(self, **kwargs):
        """
        proxy method to forward kwargs to self.model instantiation before calling queue()
        """
        return self.queue(self._queryset.model(**kwargs))

    def dump_queue(self):
        if not self._queue:
            return

        r = self._queryset.bulk_update_or_create(
            self._queue,
            self._fields,
            yield_objects=self._cb is not None,
            **self._kwargs,
        )
        if self._cb is not None:
            for st in r:
                self._cb(st)

        self._queue = []

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.dump_queue()
