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
import hashlib

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.core.cache import cache
from django.db import transaction
from django.db.models import Count
from django.http import HttpRequest
from django.shortcuts import get_object_or_404, render
from django.urls import reverse_lazy
from django.utils.text import slugify
from django.views.generic import DetailView
from django.views.generic.edit import CreateView, UpdateView
from django.views.generic.list import ListView
from rest_framework.status import HTTP_429_TOO_MANY_REQUESTS

from championship.forms import (
    AddressForm,
    EventOrganizerForm,
    RegistrationAddressForm,
    UserForm,
)
from championship.models import (
    Address,
    Event,
    EventOrganizer,
    OrganizerLeague,
    RecurringEvent,
)
from championship.score.generic import get_organizer_leaderboard
from championship.season import SEASON_2024, find_season_by_date
from championship.views.base import CustomDeleteView

ORGANIZER_LEAGUE_DESCRIPTION = "<p>A leaderboard with <b>the best players of {organizer_name} in {season_name}</b>.<br><br><i>Please note that this leaderboard is for informational purposes only and does not award any prizes, invitations or rewards.</i></p>"


class EventOrganizerDetailView(DetailView):
    model = EventOrganizer
    template_name = "championship/organizer_details.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        organizer = self.get_object()

        future_events = Event.objects.filter(
            organizer=organizer, date__gte=datetime.date.today()
        ).order_by("date")
        past_events = (
            Event.objects.filter(organizer=organizer, date__lt=datetime.date.today())
            .annotate(num_players=Count("result"))
            .order_by("-date")
        )

        all_events = []
        if future_events:
            all_events.append({"title": "Upcoming Events", "list": future_events})
        if past_events:
            all_events.append(
                {"title": "Past Events", "list": past_events, "has_num_players": True}
            )
        context["all_events"] = all_events

        # Make sure we show the final leaderboard a bit longer than the season end date
        leaderboard_offset_date = datetime.date.today() - datetime.timedelta(days=40)

        # For now we keep things simple and just show one active leaderboard
        league = OrganizerLeague.objects.filter(
            start_date__lte=datetime.date.today(),
            end_date__gte=leaderboard_offset_date,
            organizer=organizer,
        ).first()

        # If the organizer doesn't have a league, we just show a default one based on the season.
        if not league:
            season = find_season_by_date(leaderboard_offset_date)
            league = OrganizerLeague(
                organizer=organizer,
                name=f"Leaderboard of {organizer.name} in {season.name}",
                description=ORGANIZER_LEAGUE_DESCRIPTION.format(
                    organizer_name=organizer.name, season_name=season.name
                ),
                start_date=season.start_date,
                end_date=season.end_date,
                category=Event.Category.REGIONAL,
                playoffs=False,
            )

        context["league"] = league
        context["players"] = get_organizer_leaderboard(league=league)

        if organizer.user == self.request.user:
            # Show the organizer all of their own recurring events
            context["user_is_organizer"] = True
            recurring_events = RecurringEvent.objects.filter(event__organizer=organizer)
        else:
            # Show only active recurring events to other users
            recurring_events = RecurringEvent.objects.filter(
                event__organizer=organizer,
                end_date__gte=datetime.date.today(),
            )
        context["recurring_events"] = recurring_events.distinct().order_by("start_date")
        return context


class OrganizerProfileEditView(LoginRequiredMixin, UpdateView):
    template_name = "championship/update_organizer.html"
    form_class = EventOrganizerForm

    def get_object(self):
        return get_object_or_404(EventOrganizer, user=self.request.user)

    def get_success_url(self):
        return self.get_object().get_absolute_url()

    def form_valid(self, form):
        messages.success(self.request, "Succesfully updated organizer profile!")
        return super().form_valid(form)


class OrganizerListView(ListView):
    template_name = "championship/organizer_list.html"
    context_object_name = "organizers"

    def get_queryset(self):
        organizers = (
            EventOrganizer.objects.select_related("default_address")
            .annotate(num_events=Count("event"))
            .filter(num_events__gt=0)
            .order_by("name")
            .all()
        )
        organizers_with_address = [o for o in organizers if o.default_address]
        organizers_without_address = [o for o in organizers if not o.default_address]
        return (
            sorted(organizers_with_address, key=lambda o: o.default_address)
            + organizers_without_address
        )


class AddressListView(LoginRequiredMixin, ListView):
    model = Address
    template_name = "championship/address_list.html"

    def get_queryset(self):
        return self.request.user.eventorganizer.get_addresses()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["organizer_url"] = self.request.user.eventorganizer.get_absolute_url()
        return context


class AddressViewMixin:
    model = Address
    form_class = AddressForm
    template_name = "championship/address_form.html"
    success_url = reverse_lazy("address_list")

    def form_valid(self, form):
        organizer = self.request.user.eventorganizer
        form.instance.organizer = organizer
        self.object = form.save()
        if form.cleaned_data["set_as_main_address"]:
            organizer.default_address = self.object
            organizer.save()
        return super().form_valid(form)


class AddressCreateView(LoginRequiredMixin, AddressViewMixin, CreateView):
    pass


class AddressUpdateView(LoginRequiredMixin, AddressViewMixin, UpdateView):
    def get_queryset(self):
        return self.request.user.eventorganizer.get_addresses()


class AddressDeleteView(CustomDeleteView):
    model = Address
    success_url = reverse_lazy("address_list")

    def allowed_to_delete(self, address, request):
        return address.organizer.user == request.user


def is_registration_rate_limited(request: HttpRequest) -> bool:
    """Check if this registration attempt should be dropped as too often."""
    ip = request.META["REMOTE_ADDR"]
    key = "registration" + hashlib.sha256(ip.encode()).hexdigest()
    if cache.get(key):
        return True
    cache.set(key, True, settings.REGISTRATION_ATTEMPTS_MIN_INTERVAL)
    return False


@transaction.atomic
def register_event_organizer(request: HttpRequest):
    if request.method == "POST":
        user_form = UserForm(request.POST)
        organizer_form = EventOrganizerForm(request.POST, request.FILES)
        address_form = RegistrationAddressForm(request.POST)

        if (
            user_form.is_valid()
            and organizer_form.is_valid()
            and address_form.is_valid()
        ):
            user = user_form.save(commit=False)

            # Create the username based on the organizer name and the first name
            first_name = slugify(user.first_name)[:12]
            organizer_name = slugify(organizer_form.cleaned_data["name"])[:40]
            username = f"{organizer_name}_{first_name}"

            # Throw error if the username is already taken
            if User.objects.filter(username=username).exists():
                user_form.add_error(
                    None,
                    "An account with this name already exists. We will contact you shortly.",
                )
                return render(
                    request,
                    "registration/register_organizer.html",
                    {
                        "user_form": user_form,
                        "organizer_form": organizer_form,
                        "address_form": address_form,
                    },
                )

            if is_registration_rate_limited(request):
                messages.error(
                    request,
                    "You recently requested a registration, we will come back to you soon, please be patient or retry tomorrow.",
                )
                return render(
                    request,
                    "registration/register_organizer.html",
                    {
                        "user_form": user_form,
                        "organizer_form": organizer_form,
                        "address_form": address_form,
                    },
                    status=HTTP_429_TOO_MANY_REQUESTS,
                )

            user.username = username
            user.is_active = False
            user.save()

            organizer = organizer_form.save(commit=False)
            organizer.user = user
            organizer.save()

            address = address_form.save(commit=False)
            address.organizer = organizer
            address.save()

            organizer.default_address = address
            organizer.save()

            return render(request, "registration/register_organizer_success.html")
    else:
        user_form = UserForm()
        organizer_form = EventOrganizerForm()
        address_form = RegistrationAddressForm()

    context = {
        "user_form": user_form,
        "organizer_form": organizer_form,
        "address_form": address_form,
    }
    return render(request, "registration/register_organizer.html", context)
