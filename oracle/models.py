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

import uuid

from django.db import models


class Card(models.Model):
    oracle_id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    name = models.CharField(max_length=128)
    mana_cost = models.CharField(max_length=64, blank=True)
    scryfall_uri = models.CharField(max_length=128)
    mana_value = models.IntegerField()
    type_line = models.CharField(max_length=128)

    def __str__(self):
        return self.name


class AlternateName(models.Model):
    name = models.CharField(max_length=128)
    card = models.ForeignKey(Card, on_delete=models.CASCADE)


def get_card_by_name(name: str) -> Card:
    try:
        return Card.objects.get(name=name)
    except Card.DoesNotExist as e:
        try:
            return AlternateName.objects.get(name=name).card
        except AlternateName.DoesNotExist:
            raise e
