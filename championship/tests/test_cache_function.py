from django.test import TestCase
from unittest.mock import patch, ANY
import hashlib

from championship.cache_function import cache_function


@cache_function(cache_key="expensive")
def expensive():
    return 42


@cache_function(cache_key="mykey", cache_ttl=3600)
def expensive_too():
    return 42


class FunctionCacheTestCase(TestCase):
    def test_can_call_function(self):
        self.assertEqual(expensive(), 42)

    @patch("championship.cache_function.cache.set")
    def test_cache_set(self, cache_set):
        expensive()
        cache_set.assert_called_with("expensive", 42, ANY)

    @patch("championship.cache_function.cache.set")
    def test_cache_set_with_key_and_ttl(self, cache_set):
        expensive_too()
        cache_set.assert_called_with("mykey", 42, 3600)

    @patch("championship.cache_function.cache.get")
    def test_get_from_cache(self, cache_get):
        cache_get.return_value = "val"
        self.assertEqual("val", expensive_too())
