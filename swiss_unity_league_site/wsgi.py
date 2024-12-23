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

"""
WSGI config for swiss_unity_league_site project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.1/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "swiss_unity_league_site.settings")

# If we get passed a metric storage directory that does not exist, create it.
# This is required to use private tmpsfs subdirectories, such as in Docker or in
# Systemd.
if d := os.environ.get("PROMETHEUS_MULTIPROC_DIR"):
    try:
        os.makedirs(d)
    except FileExistsError:
        pass

application = get_wsgi_application()
