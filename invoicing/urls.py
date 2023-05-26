from django.urls import path, include
from . import views

urlpatterns = [path("<int:pk>/", views.RenderInvoice.as_view(), name="invoice_get")]
