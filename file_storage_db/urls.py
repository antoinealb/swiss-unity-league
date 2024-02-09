from file_storage_db.views import FileView
from django.urls import path

urlpatterns = [
    path("<path:path>", FileView.as_view(), name="file_db_serve"),
]
