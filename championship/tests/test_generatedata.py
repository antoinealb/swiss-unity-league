from django.core.management import call_command
from django.test import TestCase
from championship.models import *


class GenerateFakeDataTest(TestCase):
    def test_generate_data(self):
        call_command("generatedata", players_count=20)
        self.assertEqual(20, Player.objects.all().count())
