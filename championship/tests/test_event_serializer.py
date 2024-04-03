# Copyright 2024 Leonin League
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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
