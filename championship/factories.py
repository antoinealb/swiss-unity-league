import factory
from factory.django import DjangoModelFactory
from faker.providers import BaseProvider
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from .models import *
from .season import SEASON_2023, SEASON_2024
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


class AddressFactory(DjangoModelFactory):
    class Meta:
        model = Address

    location_name = factory.Faker("company", locale="fr_CH")
    street_address = factory.Faker("street_address", locale="fr_CH")
    city = factory.Faker("city", locale="fr_CH")
    postal_code = factory.Faker("postcode", locale="fr_CH")
    region = factory.Faker(
        "random_element",
        elements=Address.Region.values,
    )
    country = factory.Faker(
        "random_element",
        elements=Address.Country.values,
    )


class EventOrganizerFactory(DjangoModelFactory):
    class Meta:
        model = EventOrganizer

    name = factory.Faker("company", locale="fr_CH")
    contact = factory.Faker("email")
    description = factory.Faker("text")
    user = factory.SubFactory(UserFactory)

    @factory.post_generation
    def addresses(self, create, extracted, **kwargs):
        if not create:
            # Simple build, do nothing.
            return

        if extracted == None:
            # Create 3 new random addresses.
            addresses = AddressFactory.create_batch(3, organizer=self)
            for address in addresses:
                self.addresses.add(address)

            # Set one as the default
            self.default_address = addresses[0]
            self.save()


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
        start_date=SEASON_2023.start_date,
        end_date=SEASON_2023.end_date,
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


class Event2024Factory(EventFactory):
    date = factory.Faker(
        "date_between",
        start_date=SEASON_2024.start_date,
        end_date=SEASON_2024.end_date,
    )


class EventPlayerResultFactory(DjangoModelFactory):
    class Meta:
        model = EventPlayerResult

    event = factory.SubFactory(EventFactory)
    player = factory.SubFactory(PlayerFactory)
    points = factory.LazyAttribute(lambda o: 3 * o.win_count + o.draw_count)
    ranking = factory.Faker("random_int", min=1, max=30)
    win_count = factory.Faker("random_int", min=0, max=3)
    loss_count = factory.Faker("random_int", min=0, max=3)
    draw_count = factory.Faker("random_int", min=0, max=3)
