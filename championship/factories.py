import factory
from factory.django import DjangoModelFactory
from faker.providers import BaseProvider
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from .models import *
import datetime
import random


class MagicProvider(BaseProvider):
    def mtg_event_name(self):
        f = random.choice(["Modern", "Legacy", "Standard"])
        t = random.choice(["1k", "2k", "Open", "RCQ"])
        return f"{f} {t}"


factory.Faker.add_provider(MagicProvider)


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Faker("email")
    password = factory.LazyFunction(lambda: make_password("foobar"))


class EventOrganizerFactory(DjangoModelFactory):
    class Meta:
        model = EventOrganizer

    name = factory.Faker("company", locale="fr_CH")
    contact = factory.Faker("email")
    user = factory.SubFactory(UserFactory)


class PlayerFactory(DjangoModelFactory):
    class Meta:
        model = Player

    name = factory.Faker("name", locale="fr_CH")


class EventFactory(DjangoModelFactory):
    class Meta:
        model = Event

    name = factory.Faker("mtg_event_name")
    organizer = factory.SubFactory(EventOrganizerFactory)
    date = factory.Faker(
        "date_between",
        start_date=datetime.date(2022, 1, 1),
        end_date=datetime.date(2022, 9, 10),
    )
    url = factory.Faker("uri")

    format = factory.Faker(
        "random_element",
        elements=Event.Format.values,
    )

    category = factory.Faker(
        "random_element",
        elements=Event.Category.values,
    )
