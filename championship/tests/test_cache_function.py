# Copyright 2024 Leonin League
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from unittest.mock import ANY, patch

from django.test import TestCase

from championship.cache_function import cache_function


@cache_function(cache_key="expensive")
def expensive():
    return 42


@cache_function(cache_key="mykey", cache_ttl=3600)
def expensive_too():
    return 42


def cache_key(*args, **kwargs):
    return "myvarkey" + str(args[0])


@cache_function(cache_key=cache_key)
def expensive_but_with_args(x):
    return x**10


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

    @patch("championship.cache_function.cache.set")
    def test_set_cache_custom_lookup_key(self, cache_set):
        expensive_but_with_args(10)
        cache_set.assert_called_with("myvarkey10", ANY, ANY)

    @patch("championship.cache_function.cache.get")
    def test_get_cache_custom_lookup_key(self, cache_get):
        cache_get.return_value = 42
        self.assertEqual(42, expensive_but_with_args(10))
