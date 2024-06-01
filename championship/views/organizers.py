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

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Count
from django.shortcuts import get_object_or_404, render
from django.urls import reverse_lazy
from django.utils.text import slugify
from django.views.generic import DetailView
from django.views.generic.edit import CreateView, UpdateView
from django.views.generic.list import ListView

from championship.forms import (
    AddressForm,
    EventOrganizerForm,
    RegistrationAddressForm,
    UserForm,
)
from championship.models import Address, Event, EventOrganizer
from championship.views.base import CustomDeleteView


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
            .annotate(num_players=Count("eventplayerresult"))
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
        if form.cleaned_data["set_as_organizer_address"]:
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


@transaction.atomic
def register_event_organizer(request):
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
