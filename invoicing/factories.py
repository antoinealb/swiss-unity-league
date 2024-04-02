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

import datetime

import factory
from factory.django import DjangoModelFactory

from championship.factories import EventOrganizerFactory

from .models import Invoice, PayeeAddress


class PayeeAddressFactory(DjangoModelFactory):
    class Meta:
        model = PayeeAddress

    address = factory.Faker("address")


class InvoiceFactory(DjangoModelFactory):
    class Meta:
        model = Invoice

    event_organizer = factory.SubFactory(EventOrganizerFactory)
    start_date = factory.Faker(
        "date_between",
        start_date=datetime.date(2022, 1, 1),
        end_date=datetime.date(2022, 3, 31),
    )
    end_date = factory.Faker(
        "date_between",
        start_date=datetime.date(2022, 4, 1),
        end_date=datetime.date(2022, 7, 1),
    )
    payee_address = factory.SubFactory(PayeeAddressFactory)
