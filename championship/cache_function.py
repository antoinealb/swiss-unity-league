from django.core.cache import cache


def cache_function(cache_key, cache_ttl=60):
    def wrap(f):
        def wrapped(*args, **kwargs):
            if callable(cache_key):
                k = cache_key(*args, **kwargs)
            else:
                k = cache_key

            if (cached := cache.get(k)) is not None:
                return cached

            res = f(*args, **kwargs)
            cache.set(k, res, cache_ttl)
            return res

        return wrapped

    return wrap
