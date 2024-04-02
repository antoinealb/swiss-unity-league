import uuid
from zlib import crc32

from django.db import models
from django.urls import reverse

from championship.models import Event, EventOrganizer, EventPlayerResult
from championship.season import SEASON_2023, SEASON_2024, find_season_by_date

FEE_PER_PLAYER = {
    SEASON_2023: {
        Event.Category.REGULAR: 0,
        Event.Category.REGIONAL: 2,
        Event.Category.PREMIER: 3,
    },
    SEASON_2024: {
        Event.Category.REGULAR: 0,
        Event.Category.REGIONAL: 1,
        Event.Category.PREMIER: 2,
    },
}

TOP8_FEE = {
    SEASON_2023: {
        Event.Category.REGIONAL: 15,
        Event.Category.PREMIER: 75,
    },
    SEASON_2024: {
        Event.Category.REGIONAL: 20,
        Event.Category.PREMIER: 100,
    },
}


def fee_for_event(event: Event) -> int:
    season = find_season_by_date(event.date)
    if season is None:
        raise ValueError(f"Unknown season for date {event.date}")

    results = EventPlayerResult.objects.filter(event=event)
    has_top8 = results.filter(single_elimination_result__gt=0).count() > 0

    fee = results.count() * FEE_PER_PLAYER[season][event.category]

    if has_top8:
        fee += TOP8_FEE[season][event.category]

    return fee


class PayeeAddress(models.Model):
    """Informations for payment. Added at the end of an invoice PDF."""

    name = models.CharField(max_length=200)
    address = models.TextField(blank=False)
    email = models.EmailField()
    banking_coordinates = models.TextField(
        blank=False, help_text="Banking coordinates, i.e. IBAN, BIC, address"
    )

    def __str__(self) -> str:
        addr = self.address.replace("\n", " ")
        return f"{self.name} {addr}"


class Invoice(models.Model):
    """All the information required for a single invoice.

    We assume that all events in between the start date and end date need to be
    included in that invoice.
    """

    created_date = models.DateField(
        auto_now_add=True,
        help_text="Creation date, will be used as date in the PDF",
        null=False,
    )
    event_organizer = models.ForeignKey(EventOrganizer, on_delete=models.PROTECT)
    start_date = models.DateField(help_text="Start of the invoicing period")
    end_date = models.DateField(help_text="End of invoicing period")
    discount = models.IntegerField(help_text="Flat discount in CHF", default=0)
    payment_received_date = models.DateField(null=True, blank=True)
    sent_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date at which we sent the invoice to an organizer.",
    )
    notes = models.TextField(
        help_text="Notes about this invoice, only visible by Unity League staff.",
        blank=True,
    )
    payee_address = models.ForeignKey(PayeeAddress, on_delete=models.PROTECT)

    def frozen_file_upload_to(instance: "Invoice", filename: str) -> str:
        # We return an UUID so that it will not collide.
        uid = str(uuid.uuid4())
        return f"invoices/{uid}.pdf"

    frozen_file = models.FileField(
        null=True,
        blank=True,
        help_text="Cached PDF output, to prevent invoices from changing once they are correct.",
        upload_to=frozen_file_upload_to,
    )

    def __str__(self) -> str:
        fmt = "%d.%m.%Y"
        start = self.start_date.strftime(fmt)
        end = self.end_date.strftime(fmt)
        return f"{self.event_organizer.name} ({start} - {end})"

    @property
    def events(self) -> models.QuerySet[Event]:
        return self.event_organizer.event_set.filter(
            date__gte=self.start_date,
            date__lte=self.end_date,
            include_in_invoices=True,
        ).exclude(category=Event.Category.REGULAR)

    @property
    def reference(self) -> str:
        """The reference number, for payers to include in their banking order."""
        if self.id is None:
            return "SUL###-####"

        crc = crc32(str(self.id).encode()) % 1_000

        return f"SUL{self.id:03d}-{crc:03d}"

    @property
    def total_amount(self) -> int:
        """Returns total amount of the invoice, in Swiss francs."""
        return sum(fee_for_event(e) for e in self.events) - self.discount

    @property
    def is_paid(self) -> bool:
        return self.payment_received_date is not None

    def get_absolute_url(self):
        return reverse("invoice_get", args=[self.id])
