from django.test import TestCase

from championship.factories import AddressFactory, EventFactory, EventOrganizerFactory
from championship.models import Address
from championship.serializers import EventSerializer


class EventSerializerGetAddressTestCase(TestCase):
    def setUp(self):
        self.organizer_with_address = EventOrganizerFactory()
        default_address = self.organizer_with_address.default_address
        default_address.city = "Bern"
        default_address.region = Address.Region.BERN
        default_address.country = Address.Country.GERMANY
        default_address.save()
        self.organizer_without_address = EventOrganizerFactory(addresses=[])

        self.event_with_address = EventFactory(
            organizer=self.organizer_with_address,
            address=AddressFactory(
                city="Aarau",
                region=Address.Region.AARGAU,
                country=Address.Country.SWITZERLAND,
                organizer=self.organizer_with_address,
            ),
        )

        self.event_without_address = EventFactory(organizer=self.organizer_with_address)

        self.event_with_no_address_or_organizer_address = EventFactory(
            organizer=self.organizer_without_address
        )

    def test_get_address_with_event_address(self):
        serializer = EventSerializer(self.event_with_address)
        self.assertEqual(
            serializer.get_shortAddress(self.event_with_address),
            f", Aarau, {Address.Region.AARGAU.label}",
        )

    def test_get_region_with_organizer_default_address(self):
        serializer = EventSerializer(self.event_without_address)
        self.assertEqual(
            serializer.get_shortAddress(self.event_without_address),
            f", Bern, {Address.Country.GERMANY.label}",
        )

    def test_get_region_with_no_address(self):
        serializer = EventSerializer(self.event_with_no_address_or_organizer_address)
        self.assertEqual(
            serializer.get_shortAddress(
                self.event_with_no_address_or_organizer_address
            ),
            "",
        )
