import datetime

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import DetailView
from django.views.generic.edit import CreateView, UpdateView
from django.views.generic.list import ListView

from championship.forms import AddressForm, OrganizerProfileEditForm
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
    form_class = OrganizerProfileEditForm

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
