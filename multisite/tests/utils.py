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

from django.test.utils import override_settings


def global_site(test_func):
    """
    Test decorator to globally set SITE_ID=2.
    """

    @wraps(test_func)
    @override_settings(SITE_ID=2)
    def wrapped(*args, **kwargs):
        return test_func(*args, **kwargs)

    return wrapped
