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
    def mana_symbol_html(self, symbol):
        return (
            f'<i class="ms ms-cost ms-{symbol}" style="margin-left: 0 !important;"></i>'
        )

    def test_render_generic_mana(self):
        want = self.mana_symbol_html(2)
        got = mana([2])
        self.assertEqual(want, got)

    def test_render_letter_mana(self):
        want = self.mana_symbol_html("x") * 2
        got = mana(["X", "X"])
        self.assertEqual(want, got)

    def test_render_color_mana(self):
        want = self.mana_symbol_html("g") * 2
        got = mana([Color.GREEN, Color.GREEN])
        self.assertEqual(want, got)

    def test_render_phyrexian_mana(self):
        want = self.mana_symbol_html("wp")
        got = mana([Phyrexian(Color.WHITE)])
        self.assertEqual(want, got)

    def test_render_hybrid(self):
        want = self.mana_symbol_html("gu")
        got = mana([Hybrid((Color.GREEN, Color.BLUE))])
        self.assertEqual(want, got)

    def test_render_hybrid_phyrexian(self):
        want = self.mana_symbol_html("gup")
        got = mana([Phyrexian(Hybrid((Color.GREEN, Color.BLUE)))])
        self.assertEqual(want, got)

    def test_render_hybrid_generic(self):
        want = self.mana_symbol_html("2u")
        got = mana([Hybrid((2, Color.BLUE))])
        self.assertEqual(want, got)

    def test_render_hybrid_colorless(self):
        want = self.mana_symbol_html("cu")
        got = mana([Hybrid((Colorless, Color.BLUE))])
        self.assertEqual(want, got)

    def test_render_snow_mana(self):
        want = self.mana_symbol_html("s")
        got = mana([Snow])
        self.assertEqual(want, got)

    def test_render_colorless_mana(self):
        want = self.mana_symbol_html("c")
        got = mana([Colorless])
        self.assertEqual(want, got)

    def test_conversion_first(self):
        want = self.mana_symbol_html("2")
        got = mana("{2}")
        self.assertEqual(want, got)

    def test_alternative_mana(self):
        want = f'{self.mana_symbol_html(2)} // {self.mana_symbol_html("r")}'
        got = mana(AlternativeMana([[2], [Color.RED]]))
        self.assertEqual(want, got)

    def test_badparse(self):
        want = "@"
        got = mana("@")
        self.assertEqual(want, got)
