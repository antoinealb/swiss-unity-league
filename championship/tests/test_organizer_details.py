from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from championship.factories import AddressFactory, EventOrganizerFactory, EventFactory
from django.contrib.auth import get_user_model
from championship.models import Address

User = get_user_model()


class EventOrganizerDetailViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="12345")
        self.client.login(username="testuser", password="12345")

        self.organizer = EventOrganizerFactory(user=self.user)

        tomorrow = timezone.now() + timezone.timedelta(days=1)
        past_date = timezone.now() - timezone.timedelta(days=5)

        self.future_event = EventFactory(organizer=self.organizer, date=tomorrow)
        self.past_event = EventFactory(organizer=self.organizer, date=past_date)
        self.response = self.client.get(
            reverse("organizer_details", args=[self.organizer.id])
        )

    def test_organizer_detail_view(self):
        self.assertEqual(self.response.status_code, 200)
        self.assertTemplateUsed(self.response, "championship/organizer_details.html")
        self.assertContains(self.response, self.organizer.name)
        self.assertContains(self.response, self.future_event.name)
        self.assertContains(self.response, self.past_event.name)

    def test_organizer_detail_future_and_past(self):
        self.assertTrue("all_events" in self.response.context)
        self.assertEqual(len(self.response.context["all_events"]), 2)
        # Test Future Events
        self.assertEqual(
            self.response.context["all_events"][0]["list"][0], self.future_event
        )
        # Test Past Events
        self.assertEqual(
            self.response.context["all_events"][1]["list"][0], self.past_event
        )

    def test_organizer_detail_view_no_organizer(self):
        self.response = self.client.get(
            reverse("organizer_details", args=[9999])
        )  # assuming 9999 is an invalid ID
        self.assertEqual(self.response.status_code, 404)

    def test_organizer_reverse(self):
        edit_organizer_url = reverse("organizer_update")
        self.assertContains(self.response, f'href="{edit_organizer_url}"')


class OrganizerListViewTest(TestCase):
    def test_order_of_organizers(self):
        self.client = Client()
        none_tuple = (5, None, None, None)
        reversed_addresses = [
            (0, Address.Region.AARGAU, "AR", Address.Country.SWITZERLAND),
            (1, Address.Region.BERN, "aB", Address.Country.SWITZERLAND),
            (2, Address.Region.BERN, "B", Address.Country.SWITZERLAND),
            (3, Address.Region.FREIBURG_DE, "B", Address.Country.FRANCE),
            (4, Address.Region.FREIBURG_DE, "B", Address.Country.GERMANY),
            none_tuple,
        ][::-1]
        self.assertEqual(reversed_addresses[0], none_tuple)
        created_addresses = dict()
        for order, region, city, country in reversed_addresses:
            to = EventOrganizerFactory(addresses=[])
            EventFactory(organizer=to)
            if region:
                adr = AddressFactory(
                    organizer=to, region=region, city=city, country=country
                )
                to.default_address = adr
                to.save()
            else:
                adr = None
            created_addresses[order] = adr

        # create TO without events, so they shouldn't show up in list
        EventOrganizerFactory()

        response = self.client.get(reverse("organizer_view"))

        retreived_addresses = [
            o.default_address for o in response.context["organizers"]
        ]
        for index, address in enumerate(retreived_addresses):
            self.assertEquals(
                address, created_addresses[index], f"Address at index {index} was wrong"
            )
