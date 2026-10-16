from django.apps import AppConfig


class RichtextLinkConfig(AppConfig):
    name = "richtext_link"
    verbose_name = "Richtext link"

    def ready(self):
        from richtext_link import checks, guards  # noqa: F401 - system checks

        guards.connect()
