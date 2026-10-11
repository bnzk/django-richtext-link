from django.contrib import admin
from django.db import models
from django.forms import widgets
from django.http import Http404, JsonResponse
from django.urls import path
from django.utils.text import capfirst


class DjangoLinkAdmin(admin.ModelAdmin):
    # quick search over all fk link targets, on top of the dialog form
    link_search = True
    link_search_limit = 10

    def get_model_perms(self, request):
        """
        Return empty perms dict thus hiding the model from admin index.
        """
        return {}

    @property
    def media(self):
        original_media = super().media
        css = {"all": ("richtext_link/css/link_admin.css",)}
        js = ()
        if self.link_search and self._get_searchable_targets():
            js = ("richtext_link/js/link_admin_search.js",)
        return original_media + widgets.Media(css=css, js=js)

    def get_urls(self):
        """
        add verify and search urls.
        """
        my_urls = [
            path(
                "verify/",
                self.admin_site.admin_view(self.verify),
                name=self._get_verify_url_name(),
            ),
            path(
                "search/",
                self.admin_site.admin_view(self.search),
                name=self._get_search_url_name(),
            ),
        ]
        return my_urls + super().get_urls()

    def _get_verify_url_name(self):
        return f"{self.model._meta.app_label}_{self.model._meta.model_name}_verify"

    def _get_search_url_name(self):
        return f"{self.model._meta.app_label}_{self.model._meta.model_name}_search"

    def _get_searchable_targets(self):
        """
        (field, target model admin) per foreign key field of the link model
        whose target model has an admin with search_fields.
        """
        targets = []
        for field in self.model._meta.get_fields():
            if not (field.is_relation and field.many_to_one and field.related_model):
                continue
            model_admin = self.admin_site._registry.get(field.related_model)
            if model_admin and model_admin.search_fields:
                targets.append((field, model_admin))
        return targets

    def search(self, request):
        """
        search all foreign key link targets at once, based on each target
        admin's search_fields - backend of the dialog's quick search field.
        """
        if not self.link_search:
            raise Http404()
        term = request.GET.get("term", "").strip()
        groups = []
        if term:
            for field, model_admin in self._get_searchable_targets():
                if not model_admin.has_view_permission(request):
                    continue
                queryset = model_admin.get_queryset(request)
                queryset, may_have_duplicates = model_admin.get_search_results(
                    request, queryset, term
                )
                if may_have_duplicates:
                    queryset = queryset.distinct()
                items = [
                    {"id": obj.pk, "text": str(obj)}
                    for obj in queryset[: self.link_search_limit]
                ]
                if items:
                    groups.append(
                        {
                            "field": field.name,
                            "label": str(capfirst(field.verbose_name)),
                            "items": items,
                        }
                    )
        return JsonResponse({"term": term, "groups": groups})

    def verify(self, request):
        """
        verify data with modelform, send through data.
        """
        form = self.get_form(request)(request.POST)
        if form.is_valid():
            verified_data = form.cleaned_data
            obj = self.model(**verified_data)
            link_value = ""
            # prepopulate href
            if getattr(obj, "get_link", None):
                link_value = obj.get_link()
            # basic serialize only
            for key, value in verified_data.items():
                if isinstance(value, models.Model):
                    verified_data[key] = value.id
            return_data = {
                "valid": "true",
                "data": verified_data,
                "link_value": link_value,
            }
        else:
            errors = {
                field: [str(message) for message in messages]
                for field, messages in form.errors.items()
            }
            return_data = {"valid": "false", "errors": errors}
        return JsonResponse(return_data)

    def save_model(self, request, obj, form, change):
        """
        no save!
        """
        return False
