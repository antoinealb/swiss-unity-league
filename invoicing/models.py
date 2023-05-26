from typing import Iterable
import datetime
from django.db import models
from django.urls import reverse
from championship.models import EventOrganizer, Event


class Invoice(models.Model):
    """All the information required for a single invoice.

    We assume that all events in between the start date and end date need to be
    included in that invoice.
    """

    event_organizer = models.ForeignKey(EventOrganizer, on_delete=models.PROTECT)
    start_date = models.DateField(help_text="Start of the invoicing period")
    end_date = models.DateField(help_text="End of invoicing period")

    def __str__(self) -> str:
        fmt = "%d.%m.%Y"
        start = self.start_date.strftime(fmt)
        end = self.end_date.strftime(fmt)
        return f"{self.event_organizer.name} ({start} - {end})"

    @property
    def events(self) -> Iterable[Event]:
        return self.event_organizer.event_set.filter(
            date__gte=self.start_date, date__lte=self.end_date
        )

    def get_absolute_url(self):
        return reverse("invoice_get", args=[self.id])
