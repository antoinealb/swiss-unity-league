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

import mimetypes

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.views import View

from file_storage_db.models import File


class FileView(View):
    def get(self, request, path, *args, **kwargs):
        path = path.lstrip("/")
        file = get_object_or_404(File, filename=path)
        likely_type = mimetypes.guess_type(path)[0]
        return HttpResponse(file.content, content_type=likely_type)
