from django.test import TestCase

from championship.factories import AddressFactory, EventFactory, EventOrganizerFactory
from championship.models import Address
from championship.serializers import EventSerializer


class EventSerializerGetRegionTestCase(TestCase):
    def setUp(self):
        self.organizer_with_address = EventOrganizerFactory()
        self.organizer_with_address.default_address.region = Address.Region.BERN
        self.organizer_with_address.default_address.save()
        self.organizer_without_address = EventOrganizerFactory(addresses=[])

        self.event_with_address = EventFactory(
            organizer=self.organizer_with_address,
            address=AddressFactory(
                region=Address.Region.AARGAU, organizer=self.organizer_with_address
            ),
        )

        self.event_without_address = EventFactory(organizer=self.organizer_with_address)

        self.event_with_no_address_or_organizer_address = EventFactory(
            organizer=self.organizer_without_address
        )

    def test_get_region_with_event_address(self):
        serializer = EventSerializer(self.event_with_address)
        self.assertEqual(
            serializer.get_region(self.event_with_address),
            Address.Region.AARGAU.label,
        )

    def test_get_region_with_organizer_default_address(self):
        serializer = EventSerializer(self.event_without_address)
        self.assertEqual(
            serializer.get_region(self.event_without_address), Address.Region.BERN.label
        )

    def test_get_region_with_no_address(self):
        serializer = EventSerializer(self.event_with_no_address_or_organizer_address)
        self.assertEqual(
            serializer.get_region(self.event_with_no_address_or_organizer_address), ""
        )
