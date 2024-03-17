from django.conf import settings
from django.db import models
from django.urls import reverse


class File(models.Model):
    filename = models.CharField(max_length=4096, primary_key=True)
    content = models.BinaryField()

    def get_absolute_url(self):
        return reverse("file_db_serve", args=[self.filename])


if "auditlog" in settings.INSTALLED_APPS:
    from auditlog.registry import auditlog

    auditlog.register(File, exclude_fields=["content"])
