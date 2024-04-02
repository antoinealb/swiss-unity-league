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

from django.core import files
from django.core.exceptions import ObjectDoesNotExist
from django.core.files.storage import Storage
from django.urls import reverse

from file_storage_db.models import File


class DatabaseFileStorage(Storage):
    def exists(self, name: str):
        return File.objects.filter(filename=name).exists()

    def _save(self, name: str, content: files.File) -> str:
        f = File.objects.create(filename=name, content=content.read())
        return name

    def _open(self, name, mode="rb"):
        try:
            f = File.objects.get(filename=name)
        except File.DoesNotExist:
            raise FileNotFoundError(f"No file named {name}")

        if mode == "r":
            content = f.content.decode()
        elif mode == "rb":
            content = f.content
        else:
            raise PermissionError(f"Mode '{mode}' is not supported")

        return files.base.ContentFile(content=content, name=name)

    def size(self, name):
        try:
            f = File.objects.get(filename=name)
        except File.DoesNotExist:
            raise FileNotFoundError(f"No file named {name}")

        return len(f.content)

    def delete(self, name):
        try:
            f = File.objects.get(filename=name)
        except File.DoesNotExist:
            raise FileNotFoundError(f"No file named {name}")
        f.delete()

    def url(self, name):
        return reverse("file_db_serve", args=[name])
