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

from django.contrib.auth.models import User
from django.db.models import ProtectedError
from django.test import TestCase

from championship.factories import EventFactory, EventOrganizerFactory
from championship.models import EventOrganizer


class EventOrganizerTest(TestCase):
    def test_can_be_deleted_by_deleting_user(self):
        """Checks that we are allowed to delete EventOrganizer by deleting the
        associated user."""
        eo = EventOrganizerFactory()
        User.objects.filter(id=eo.user.id).delete()
        self.assertFalse(EventOrganizer.objects.all().exists())

    def test_cannot_delete_if_associated_events(self):
        """
        Checks that organizers with events cannot be deleted by accident
        through deleting their user.
        """
        eo = EventOrganizerFactory()
        EventFactory(organizer=eo)

        with self.assertRaises(ProtectedError):
            User.objects.filter(id=eo.user.id).delete()
