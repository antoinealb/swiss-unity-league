from django.urls import path, include
from . import views

urlpatterns = [
    path("", views.InvoiceList.as_view(), name="invoice_list"),
    path("<int:pk>/", views.RenderInvoice.as_view(), name="invoice_get"),
]
