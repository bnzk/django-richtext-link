from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from richtext_link.tests.test_app.models import LinkModel, TestModel


class DjangoLinkAdminVerifyTests(TestCase):
    fixtures = [
        "test_app.json",
    ]

    def setUp(self):
        self.user = User.objects.create_superuser("admin", "admin@bnzk.ch", "admin")
        self.client.force_login(self.user)
        self.verify_url = reverse("admin:test_app_linkmodel_verify")
        self.add_url = reverse("admin:test_app_linkmodel_add")

    def test_verify_valid_fk(self):
        response = self.client.post(
            self.verify_url,
            {"testmodel": "1", "external_url": "", "email": "", "target": ""},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["valid"], "true")
        # fk serialized to its pk
        self.assertEqual(data["data"]["testmodel"], 1)
        self.assertEqual(data["link_value"], "/testmodel/1/")

    def test_verify_invalid(self):
        response = self.client.post(
            self.verify_url,
            {"email": "no-email", "external_url": "", "target": ""},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["valid"], "false")
        self.assertIn("email", data["errors"])
        self.assertTrue(len(data["errors"]["email"]))

    def test_verify_multiwidget_date(self):
        response = self.client.post(
            self.verify_url,
            {
                "when_year": "2018",
                "when_month": "2",
                "when_day": "3",
                "external_url": "",
                "email": "",
                "target": "",
            },
        )
        data = response.json()
        self.assertEqual(data["valid"], "true")
        self.assertEqual(data["data"]["when"], "2018-02-03")
        self.assertEqual(data["link_value"], "2018-02-03")

    def test_verify_never_saves(self):
        self.client.post(
            self.verify_url,
            {"external_url": "http://x.com/", "email": "", "target": ""},
        )
        self.assertEqual(LinkModel.objects.count(), 0)

    def test_add_form_prefill(self):
        response = self.client.get(self.add_url, {"_popup": "1", "target": "abc"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'value="abc"')

    def test_verify_requires_login(self):
        self.client.logout()
        response = self.client.post(self.verify_url, {})
        # admin_view wraps: redirect to admin login
        self.assertEqual(response.status_code, 302)

    def test_link_model_hidden_from_admin_index(self):
        response = self.client.get(reverse("admin:index"))
        self.assertNotContains(response, "Link model")

    def test_testmodel_deletable_by_default(self):
        # RICHTEXT_LINK_INDEX_PROTECT is off: deleting a linked object works
        TestModel.objects.get(pk=1).delete()
        self.assertFalse(TestModel.objects.filter(pk=1).exists())
