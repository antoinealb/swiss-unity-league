from championship.factories import EventPlayerResultFactory
from django.test import TestCase


class EventPlayerResultFactoryTest(TestCase):
    def test_score_is_computed_automatically(self):
        p = EventPlayerResultFactory(win_count=3, draw_count=1)
        self.assertEqual(10, p.points)
