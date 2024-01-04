from django.test import TestCase
from django.urls import reverse
from parameterized import parameterized
from championship.season import SEASONS_WITH_INFO


class InfoPlayerViewTest(TestCase):
    @parameterized.expand(SEASONS_WITH_INFO)
    def test_seasons_exist(self, season):
        url = reverse("info_for_season", kwargs={"slug": season.slug})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, f"championship/info/{season.id}/info_player.html"
        )

    def test_default_info_exists(self):
        response = self.client.get(reverse("info"))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(
            reverse("info_for_season", kwargs={"slug": "foobar"})
        )
        self.assertEqual(response.status_code, 200)


class InfoOrganizerViewTest(TestCase):
    @parameterized.expand(SEASONS_WITH_INFO)
    def test_seasons_exist(self, season):
        url = reverse("info_organizer_for_season", kwargs={"slug": season.slug})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, f"championship/info/{season.id}/info_organizer.html"
        )

    def test_default_info_exists(self):
        response = self.client.get(reverse("info_organizer"))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(
            reverse("info_organizer_for_season", kwargs={"slug": "foobar"})
        )
        self.assertEqual(response.status_code, 200)
