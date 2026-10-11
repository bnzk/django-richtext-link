"""URLs to run the tests."""

from django.contrib import admin
from django.urls import path

from richtext_link.tests.test_app.views import TestModelDetailView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("testmodel/<int:pk>/", TestModelDetailView.as_view(), name="testmodel_detail"),
]
