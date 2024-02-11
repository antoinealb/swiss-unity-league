from django.db import models
from django.urls import reverse
from auditlog.registry import auditlog


class File(models.Model):
    filename = models.CharField(max_length=4096, primary_key=True)
    content = models.BinaryField()

    def get_absolute_url(self):
        return reverse("file_db_serve", args=[self.filename])


auditlog.register(File, exclude_fields=["content"])
