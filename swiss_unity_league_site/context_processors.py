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

from django.conf import settings
from django.contrib.sites.models import Site

from multisite.constants import GLOBAL_DOMAIN, SWISS_DOMAIN


def debug(request):
    """Adds a debug variable reflecting the site's DEBUG value.

    The reason we are not using django.template.context_processors.debug is
    that it requires both a debug IP and a DEBUG instance, which is not
    possible with the way the SUL playground is setup.
    """
    return {"debug": settings.DEBUG}


def current_site(request):
    """
    Provides a context variable to the email address for public contact.
    """
    site = Site.objects.get_current()
    return {
        "SITE": site,
        "SITE_SETTINGS": site.site_settings,
        "IS_SWISS_SITE": site.domain == SWISS_DOMAIN,
        "IS_GLOBAL_SITE": site.domain == GLOBAL_DOMAIN,
    }
