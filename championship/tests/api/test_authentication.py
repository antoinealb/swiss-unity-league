from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_403_FORBIDDEN,
)
from rest_framework.test import APITestCase


class ObtainTokenTest(APITestCase):
    def setUp(self):
        self.credentials = dict(username="test", password="test")
        self.user = User.objects.create_user(**self.credentials)

    def test_obtain_token(self):
        resp = self.client.post(reverse("api_auth_token"), data=self.credentials)
        self.assertEqual(HTTP_200_OK, resp.status_code)
        self.assertIn("token", resp.json())

    def test_wrong_credentials(self):
        self.credentials["password"] = "foo"
        resp = self.client.post(reverse("api_auth_token"), data=self.credentials)
        self.assertNotEqual(HTTP_200_OK, resp.status_code)
