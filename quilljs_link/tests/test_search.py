from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from quilljs_link.tests.test_app.models import TestModel


class DjangoLinkAdminSearchTests(TestCase):
    fixtures = [
        "test_app.json",
    ]

    def setUp(self):
        self.user = User.objects.create_superuser("admin", "admin@bnzk.ch", "admin")
        self.client.force_login(self.user)
        self.search_url = reverse("admin:test_app_linkmodel_search")

    def test_search_finds_targets(self):
        response = self.client.get(self.search_url, {"term": "Legacy"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["groups"]), 1)
        group = data["groups"][0]
        self.assertEqual(group["field"], "testmodel")
        self.assertEqual(group["label"], "Testmodel")
        self.assertEqual(group["items"], [{"id": 3, "text": "Legacy CKEditor content"}])

    def test_search_empty_term(self):
        response = self.client.get(self.search_url)
        self.assertEqual(response.json()["groups"], [])
        response = self.client.get(self.search_url, {"term": "  "})
        self.assertEqual(response.json()["groups"], [])

    def test_search_no_match(self):
        response = self.client.get(self.search_url, {"term": "nosuchthing"})
        self.assertEqual(response.json()["groups"], [])

    def test_search_limit(self):
        for count in range(15):
            TestModel.objects.create(title=f"Bulk {count}")
        response = self.client.get(self.search_url, {"term": "Bulk"})
        group = response.json()["groups"][0]
        self.assertEqual(len(group["items"]), 10)

    def test_search_requires_login(self):
        self.client.logout()
        response = self.client.get(self.search_url, {"term": "Legacy"})
        self.assertEqual(response.status_code, 302)

    def test_search_without_fk_targets(self):
        # ContribLinkModel has no foreign key fields - endpoint stays empty
        url = reverse("admin:test_app_contriblinkmodel_search")
        response = self.client.get(url, {"term": "Legacy"})
        self.assertEqual(response.json()["groups"], [])

    def test_search_js_only_with_searchable_targets(self):
        response = self.client.get(
            reverse("admin:test_app_linkmodel_add"), {"_popup": "1"}
        )
        self.assertContains(response, "quilljs_link/js/link_admin_search.js")
        response = self.client.get(
            reverse("admin:test_app_contriblinkmodel_add"), {"_popup": "1"}
        )
        self.assertNotContains(response, "quilljs_link/js/link_admin_search.js")


class LinkBaseAdminStashTests(TestCase):
    """
    The contrib LinkBaseAdmin uses django-formfieldstash (installed in the
    test env): the dialog form only shows the selected link_type's field.
    """

    def setUp(self):
        self.user = User.objects.create_superuser("admin", "admin@bnzk.ch", "admin")
        self.client.force_login(self.user)

    def test_stash_applied_on_contrib_admin(self):
        response = self.client.get(
            reverse("admin:test_app_contriblinkmodel_add"), {"_popup": "1"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "formfield_stash/formfield_stash.js")
        self.assertContains(response, 'data-formfield-stash="true"')
        self.assertContains(response, 'data-original-field="link_type"')
        # link_type/link_style render as selects (formfieldstash needs selects)
        self.assertContains(response, '<select name="link_type"')
        self.assertContains(response, '<select name="link_style"')

    def test_stash_not_applied_on_plain_admin(self):
        response = self.client.get(
            reverse("admin:test_app_linkmodel_add"), {"_popup": "1"}
        )
        self.assertNotContains(response, "formfield_stash/formfield_stash.js")
