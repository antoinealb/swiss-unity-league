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

from functools import wraps

from django.contrib.sites.models import Site
from django.test.utils import override_settings


def site(domain):
    """
    Test decorator or context manager to set SITE_ID based on the given domain.
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

        def __call__(self, test_func):
            @wraps(test_func)
            def wrapped(*args, **kwargs):
                with self:
                    return test_func(*args, **kwargs)

            return wrapped

    return SiteContext(domain)
