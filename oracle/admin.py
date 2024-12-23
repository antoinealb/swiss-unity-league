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

from django.contrib import admin

from oracle.models import Card


class CardAdmin(admin.ModelAdmin):
    list_display = ("name", "mana_cost", "mana_value", "type_line")
    search_fields = ("name", "type_line")
    list_filter = ("mana_value",)

    # Cards are created through a management command to import data from
    # Scryfall. We do not want people adding or modifying the content of the
    # Cards manually, but want them to be able to see the objects.
    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


admin.site.register(Card, CardAdmin)
