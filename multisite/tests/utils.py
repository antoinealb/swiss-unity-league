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

import inspect
from functools import wraps

from django.contrib.sites.models import Site
from django.test import TestCase, override_settings


def with_site(domain):
    """
    Test decorator or context manager to set SITE_ID based on the given domain.

    Usage:
    This utility is designed to facilitate testing in a Django application where the
    SITE_ID needs to be dynamically set based on a specific domain within test cases.

    As a Decorator:
    - When applied to a test method, it will wrap the method execution within the site
      context, ensuring that SITE_ID is set appropriately while the test runs.
    - When applied to a unittest.TestCase class, it will modify the setUpClass
      and tearDownClass methods to manage the site context for the entire suite
      of tests under that class.

    As a Context Manager:
    - It can be used directly in a 'with' statement inside test methods to temporarily set
      the SITE_ID for a specific block of code.

    Example:
    @site('example.com')
    class MyTestCase(TestCase):

        def test_something(self):
            # Test code here will run with SITE_ID set to the ID of 'example.com'

        @sites('another-example.com')
        def test_other(self):
            # Test code here will run with SITE_ID set to the ID of 'another-example.com'

    or

    class MyOtherTestCase(TestCase):
        def test_another_thing(self):
            with site('example.com'):
                # This block runs with SITE_ID set to the ID of 'example.com'
    """

    class SiteContext:
        def __init__(self, domain):
            self.domain = domain

        def __enter__(self):
            self.site_id = Site.objects.get(domain=self.domain).id
            self.override = override_settings(SITE_ID=self.site_id)
            self.override.enable()

        def __exit__(self, exc_type, exc_value, traceback):
            self.override.disable()

        def __call__(self, obj):
            if inspect.isclass(obj) and issubclass(obj, TestCase):
                original_setup_class = obj.setUpClass
                original_tear_down_class = obj.tearDownClass

                @classmethod
                def new_setup_class(cls):
                    self.__enter__()  # Apply the context setup
                    original_setup_class()

                @classmethod
                def new_tear_down_class(cls):
                    self.__exit__(None, None, None)  # Clean up the context
                    original_tear_down_class()

                obj.setUpClass = new_setup_class
                obj.tearDownClass = new_tear_down_class

                return obj
            elif inspect.isfunction(obj):

                @wraps(obj)
                def wrapped(*args, **kwargs):
                    with self:
                        return obj(*args, **kwargs)

                return wrapped
            else:
                raise TypeError(
                    "Decorator can only be used on test methods or TestCase classes."
                )

    return SiteContext(domain)
