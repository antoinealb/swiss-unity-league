from django.test import TestCase
from django.urls import reverse

SEASONS_WITH_INFO = [1, 2]


class InfoPlayerViewTest(TestCase):
    def test_seasons_exist(self):
        for season_id in SEASONS_WITH_INFO:
            url = reverse("info_id", kwargs={"id": season_id})
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(
                response, f"championship/info/{season_id}/info_player.html"
            )

    def test_default_info_exists(self):
        response = self.client.get(reverse("info"))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse("info_id", kwargs={"id": 9999}))
        self.assertEqual(response.status_code, 200)


class InfoOrganizerViewTest(TestCase):
    def test_seasons_exist(self):
        for season_id in SEASONS_WITH_INFO:
            url = reverse("info_organizer_id", kwargs={"id": season_id})
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(
                response, f"championship/info/{season_id}/info_organizer.html"
            )

    def test_default_info_exists(self):
        response = self.client.get(reverse("info_organizer"))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse("info_organizer_id", kwargs={"id": 9999}))
        self.assertEqual(response.status_code, 200)
