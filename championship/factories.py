import factory
from factory.django import DjangoModelFactory
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from .models import *
import datetime


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Faker("email")
    password = factory.LazyFunction(lambda: make_password("foobar"))


class EventOrganizerFactory(DjangoModelFactory):
    class Meta:
        model = EventOrganizer

    name = factory.Faker("company")
    contact = factory.Faker("email")
    user = factory.SubFactory(UserFactory)


class PlayerFactory(DjangoModelFactory):
    class Meta:
        model = Player

    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")


class EventFactory(DjangoModelFactory):
    class Meta:
        model = Event

    name = factory.Faker("company")
    organizer = factory.SubFactory(EventOrganizerFactory)
    date = factory.Faker(
        "date_between",
        start_date=datetime.date(2022, 1, 1),
        end_date=datetime.date(2022, 9, 10),
    )
    url = factory.Faker("uri")

    format = Event.Format.MODERN
    category = factory.Faker(
        "random_element",
        elements=Event.Category.values,
    )
    ranking_type = Event.RankingType.RANKED
