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

from parameterized import parameterized

from championship.templatetags.custom_tags import initials


class InitialFilterTestCase(TestCase):
    @parameterized.expand(
        [
            ("Antoine Albertelli", "Antoine A."),
            ("Antoine Renaud-Goud", "Antoine R.-G."),
            ("Laurin van der Haegen", "Laurin v. d. H."),
        ]
    )
    def test_initial(self, name, want):
        got = initials(name)
        self.assertEqual(got, want)
