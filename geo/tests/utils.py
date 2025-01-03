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

from geopy.geocoders.base import Geocoder, Point


class FakeGeocoder(Geocoder):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def geocode(self, addr: str) -> Point:
        # Somewhere in Zürich
        return Point(47.377692, 8.534566)
