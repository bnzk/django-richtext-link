"""Settings that need to be set in order to run the tests."""
import os

DEBUG = True

HEADLESS_TESTING = True

APP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

RICHTEXT_LINK_MODEL = "richtext_link.tests.test_app.models.LinkModel"
# not a good example, but working for our tests
RICHTEXT_LINK_ATTR_MODIFIERS = {
    "target": "{target}--xy",
}
RICHTEXT_LINK_CONFIGS = {
    # the shipped tiptap schema, plus blockClasses for the editor tests
    "default": {
        "editor": "tiptap",
        "toolbar": [
            ["bold", "italic"],
            ["h2", "h3", "p"],
            ["bulletList", "orderedList"],
            ["djangolink", "clear"],
        ],
        "headingLevels": [2, 3],
        "blockClasses": {
            "paragraph": [["", "Default"], ["intro", "Intro"]],
            "heading": [["", "Default"], ["fancy", "Fancy"]],
        },
        "djangolink": {},
    },
    "quill": {
        "editor": "quilljs",
        "theme": "snow",
        "modules": {
            "toolbar": [
                ["bold", "italic", "underline"],
                [{"list": "ordered"}, {"list": "bullet"}],
                ["djangolink", "clean"],
            ],
            "djangolink": {},
        },
    },
    "ckeditor": {
        "editor": "ckeditor5",
        # served from tests/test_app/static/ when downloaded via
        # richtext_link/tests/get_ckeditor5.sh (gitignored, GPL - not shipped)
        "assets": {
            "js": "test_ckeditor5/ckeditor5.umd.js",
            "css": "test_ckeditor5/ckeditor5.css",
        },
        "licenseKey": "GPL",
        "djangolink": {},
        "ckeditor": {
            "toolbar": [
                "heading",
                "|",
                "bold",
                "italic",
                "|",
                "bulletedList",
                "numberedList",
                "|",
                "djangolink",
            ],
        },
    },
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
ROOT_URLCONF = "richtext_link.tests.urls"

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
    "richtext_link",
    "richtext_link.link_index",
    "richtext_link.tests.test_app",
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
