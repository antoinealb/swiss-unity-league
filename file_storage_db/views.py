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
