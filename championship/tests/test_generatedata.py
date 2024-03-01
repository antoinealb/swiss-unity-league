from django.core.management import call_command
from django.test import TestCase
from championship.models import *


class GenerateFakeDataTest(TestCase):
    def test_generate_data(self):
        call_command("generatedata", players_count=4, events_count=2)
        self.assertEqual(4, Player.objects.all().count())
        self.assertEqual(2, Event.objects.all().count())
