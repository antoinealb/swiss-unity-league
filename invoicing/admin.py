from django.contrib import admin
from invoicing.models import Invoice


class InvoiceAdmin(admin.ModelAdmin):
    search_fields = ["event_organizer__name"]
    list_filter = ["event_organizer"]
    date_hierarchy = "end_date"
    list_display = (
        "event_organizer_name",
        "reference",
        "amount",
        "start_date",
        "end_date",
    )

    @admin.display(ordering="id", description="Reference number")
    def reference(self, instance: Invoice) -> str:
        return instance.reference

    @admin.display(ordering="event_organizer__name", description="Organizer name")
    def event_organizer_name(self, instance: Invoice):
        return instance.event_organizer.name

    @admin.display(description="Amount")
    def amount(self, instance: Invoice) -> str:
        return f"{instance.total_amount} CHF"


admin.site.register(Invoice, InvoiceAdmin)
