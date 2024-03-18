from django.test import TestCase

from championship.factories import EventPlayerResultFactory


class EventPlayerResultFactoryTest(TestCase):
    def test_score_is_computed_automatically(self):
        p = EventPlayerResultFactory(win_count=3, draw_count=1)
        self.assertEqual(10, p.points)


class EventPlayerResultTest(TestCase):
    def test_str(self):
        p = EventPlayerResultFactory(win_count=3, draw_count=0, loss_count=2)
        self.assertEqual(f"{p.player.name}@{p.event.name} (3-2-0)", str(p))
