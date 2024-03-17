from file_storage_db.models import File
from django.core.files.storage import Storage
from django.core import files
from django.core.exceptions import ObjectDoesNotExist
from django.urls import reverse


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
