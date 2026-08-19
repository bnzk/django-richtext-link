"""Settings that need to be set in order to run the tests."""
import os

DEBUG = True

HEADLESS_TESTING = True

APP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

QUILLJS_LINK_MODEL = "quilljs_link.tests.test_app.models.LinkModel"
# not a good example, but working for our tests
QUILLJS_LINK_ATTR_MODIFIERS = {
    "target": "{target}--xy",
}

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": "db.sqlite",
    }
}

LANGUAGE_CODE = "en"
USE_TZ = True

# the link dialog is an iframe!
X_FRAME_OPTIONS = "SAMEORIGIN"
DEFAULT_AUTO_FIELD = "django.db.models.AutoField"
ROOT_URLCONF = "quilljs_link.tests.urls"

MEDIA_URL = "/media/"
STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(APP_ROOT, "../test_app_static")

INSTALLED_APPS = (
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.messages",
    "django.contrib.sessions",
    "django.contrib.staticfiles",
    "quilljs_link",
    "quilljs_link.link_index",
    "quilljs_link.tests.test_app",
    # soft dep of the contrib LinkBaseAdmin (needed for its static files)
    "formfieldstash",
)

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.i18n",
                "django.template.context_processors.request",
                "django.template.context_processors.media",
                "django.template.context_processors.static",
            ],
            "loaders": [
                "django.template.loaders.filesystem.Loader",
                "django.template.loaders.app_directories.Loader",
            ],
        },
    },
]

MIDDLEWARE = (
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django.middleware.locale.LocaleMiddleware",
)

SECRET_KEY = "foobarXXXxxsvXY"
