from django.core.cache import cache


def cache_function(cache_key, cache_ttl=60):
    def wrap(f):
        def wrapped():
            if (cached := cache.get(cache_key)) is not None:
                return cached

            res = f()
            cache.set(cache_key, res, cache_ttl)
            return res

        return wrapped

    return wrap
