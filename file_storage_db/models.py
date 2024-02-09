from django.db import models


class File(models.Model):
    filename = models.CharField(max_length=4096, primary_key=True)
    content = models.BinaryField()
