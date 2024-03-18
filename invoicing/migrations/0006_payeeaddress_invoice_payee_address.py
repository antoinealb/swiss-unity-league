# This migration is written by hand to create a default PayeeAddress for
# pre-existing invoices, before adding a constraint that every invoice has a
# non-null foreign key to a PayeeAddress.
import django.db.models.deletion
from django.db import migrations, models

DEFAULT_NAME = "Antoine Albertelli"

DEFAULT_ADDR = """Swiss Unity League
Binzallee 6
8055 Zürich"""

DEFAULT_BANKING = """IBAN: CH93 0024 3243 2366 2340 E (Bank: UBS)
Swiss Unity League
c/o Antoine Albertelli
Binzallee 6
8055 Zürich
BIC: UBSWCHZH80A"""

DEFAULT_EMAIL = "leoninleague@gmail.com"


def forward(apps, schema_editor):
    PayeeAddress = apps.get_model("invoicing", "PayeeAddress")
    addr = PayeeAddress.objects.create(
        name=DEFAULT_NAME,
        address=DEFAULT_ADDR,
        email=DEFAULT_EMAIL,
        banking_coordinates=DEFAULT_BANKING,
    )

    Invoice = apps.get_model("invoicing", "Invoice")
    Invoice.objects.update(payee_address=addr)


def backward(apps, schema_editor):
    Invoice = apps.get_model("invoicing", "Invoice")
    Invoice.objects.update(payee_address=None)

    PayeeAddress = apps.get_model("invoicing", "PayeeAddress")
    PayeeAddress.objects.filter(name=DEFAULT_NAME).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("invoicing", "0005_invoice_sent_date"),
    ]

    operations = [
        migrations.CreateModel(
            name="PayeeAddress",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=200)),
                ("email", models.EmailField()),
                ("address", models.TextField()),
                (
                    "banking_coordinates",
                    models.TextField(
                        help_text="Banking coordinates, i.e. IBAN, BIC, address"
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="invoice",
            name="payee_address",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                to="invoicing.payeeaddress",
            ),
        ),
        migrations.RunPython(forward, backward),
        # Don't allow NULL payee_address anymore
        migrations.AlterField(
            model_name="invoice",
            name="payee_address",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT, to="invoicing.payeeaddress"
            ),
        ),
    ]
