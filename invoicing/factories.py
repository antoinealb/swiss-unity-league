import datetime
import factory
from factory.django import DjangoModelFactory
from .models import Invoice
from championship.factories import EventOrganizerFactory


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
