from django.urls import path

from file_storage_db.views import FileView

urlpatterns = [
    path("<path:path>", FileView.as_view(), name="file_db_serve"),
]
