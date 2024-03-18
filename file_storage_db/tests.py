import io

from django.http import Http404
from django.test import RequestFactory, TestCase

from file_storage_db.models import File
from file_storage_db.storage import DatabaseFileStorage
from file_storage_db.views import FileView


class DatabaseFSTestCase(TestCase):
    def setUp(self):
        self.storage = DatabaseFileStorage()
        self.storage.save("test.txt", io.BytesIO(b"hello, world"))

    def test_can_save_data(self):
        f = File.objects.get(filename="test.txt")
        self.assertEqual(f.content.decode(), "hello, world")

    def test_can_open_file(self):
        f = self.storage.open("test.txt")
        self.assertEqual(f.name, "test.txt")
        self.assertEqual(f.read().decode(), "hello, world")

    def test_can_open_file_in_text_mode(self):
        f = self.storage.open("test.txt", "r")
        self.assertEqual(f.name, "test.txt")
        self.assertEqual(f.read(), "hello, world")

    def test_unknown_file(self):
        with self.assertRaises(FileNotFoundError):
            self.storage.open("non-existing.txt")

    def test_cannot_write(self):
        with self.assertRaises(PermissionError):
            self.storage.open("test.txt", "w")

    def test_storage_size(self):
        self.assertEqual(12, self.storage.size("test.txt"))

    def test_can_delete(self):
        self.storage.delete("test.txt")
        with self.assertRaises(FileNotFoundError):
            self.storage.open("test.txt")


class DatabaseFsMediaServingTest(TestCase):
    """Tests that the media serving from the DB is working as expected."""

    def setUp(self):
        self.storage = DatabaseFileStorage()
        self.file = self.storage.save("test.txt", io.BytesIO(b"hello, world"))

    def get_file(self, filename):
        request = RequestFactory().get(f"/media/{filename}")
        return FileView.as_view()(request, path=filename)

    def test_can_get_view(self):
        resp = self.get_file("test.txt")
        self.assertEqual(200, resp.status_code)
        self.assertEqual("hello, world", resp.content.decode())

    def test_can_get_another_file(self):
        self.storage.save("test_fr.txt", io.BytesIO(b"Bonjour, monde"))
        resp = self.get_file("test_fr.txt")
        self.assertEqual(200, resp.status_code)
        self.assertEqual("Bonjour, monde", resp.content.decode())

    def test_can_get_404(self):
        with self.assertRaises(Http404):
            self.get_file("test_klingon.txt")

    def test_application_mimetype(self):
        self.storage.save("test.png", io.BytesIO(b"hello"))
        resp = self.get_file("test.png")
        self.assertEqual(resp["content-type"], "image/png")

    def test_application_mimetype_webp(self):
        self.storage.save("test.webp", io.BytesIO(b"hello"))
        resp = self.get_file("test.webp")
        self.assertEqual(resp["content-type"], "image/webp")
