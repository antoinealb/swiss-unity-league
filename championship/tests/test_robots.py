from django.test import Client, TestCase


class RobotsTxtTest(TestCase):
    def test_get_robot(self):
        client = Client()
        resp = client.get("/robots.txt")
        self.assertEqual(200, resp.status_code)
