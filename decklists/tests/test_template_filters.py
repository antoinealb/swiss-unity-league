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

from unittest import TestCase

from decklists.parser import AlternativeMana, Color, Colorless, Hybrid, Phyrexian, Snow
from decklists.templatetags.mana import mana


class ManaRendererTestCase(TestCase):
    def test_render_generic_mana(self):
        want = '<i class="ms ms-cost ms-2"></i>'
        got = mana([2])
        self.assertEqual(want, got)

    def test_render_letter_mana(self):
        want = '<i class="ms ms-cost ms-x"></i>' * 2
        got = mana(["X", "X"])
        self.assertEqual(want, got)

    def test_render_color_mana(self):
        want = '<i class="ms ms-cost ms-g"></i>' * 2
        got = mana([Color.GREEN, Color.GREEN])
        self.assertEqual(want, got)

    def test_render_phyrexian_mana(self):
        want = '<i class="ms ms-cost ms-wp"></i>'
        got = mana([Phyrexian(Color.WHITE)])
        self.assertEqual(want, got)

    def test_render_hybrid(self):
        want = '<i class="ms ms-cost ms-gu"></i>'
        got = mana([Hybrid((Color.GREEN, Color.BLUE))])
        self.assertEqual(want, got)

    def test_render_hybrid_phyrexian(self):
        want = '<i class="ms ms-cost ms-gup"></i>'
        got = mana([Phyrexian(Hybrid((Color.GREEN, Color.BLUE)))])
        self.assertEqual(want, got)

    def test_render_hybrid_generic(self):
        want = '<i class="ms ms-cost ms-2u"></i>'
        got = mana([Hybrid((2, Color.BLUE))])
        self.assertEqual(want, got)

    def test_render_hybrid_generic(self):
        want = '<i class="ms ms-cost ms-cu"></i>'
        got = mana([Hybrid((Colorless, Color.BLUE))])
        self.assertEqual(want, got)

    def test_render_snow_mana(self):
        want = '<i class="ms ms-cost ms-s"></i>'
        got = mana([Snow])
        self.assertEqual(want, got)

    def test_render_colorless_mana(self):
        want = '<i class="ms ms-cost ms-c"></i>'
        got = mana([Colorless])
        self.assertEqual(want, got)

    def test_conversion_first(self):
        want = '<i class="ms ms-cost ms-2"></i>'
        got = mana("{2}")
        self.assertEqual(want, got)

    def test_alternative_mana(self):
        want = '<i class="ms ms-cost ms-2"></i> // <i class="ms ms-cost ms-r"></i>'
        got = mana(AlternativeMana([[2], [Color.RED]]))
        self.assertEqual(want, got)

    def test_badparse(self):
        want = "@"
        got = mana("@")
        self.assertEqual(want, got)
