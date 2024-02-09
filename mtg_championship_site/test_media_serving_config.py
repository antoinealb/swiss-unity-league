from django.test import TestCase, Client
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.conf import settings


class MediaServingTestCase(TestCase):
    def test_get_media(self):
        filename = "test/test.txt"
        default_storage.save(filename, ContentFile(b"hello"))
        client = Client()
        resp = client.get(f"{settings.MEDIA_URL}/{filename}")
        self.assertEqual(200, resp.status_code)
        self.assertEqual("hello", resp.content.decode())
