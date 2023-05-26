from django.contrib import admin
from invoicing.models import Invoice


class InvoiceAdmin(admin.ModelAdmin):
    search_fields = ["event_organizer__name"]
    list_display = ("event_organizer_name", "start_date", "end_date")

    @admin.display(ordering="event_organizer__name", description="Organizer name")
    def event_organizer_name(self, instance: Invoice):
        return instance.event_organizer.name


admin.site.register(Invoice, InvoiceAdmin)
