import os
import shutil
import unittest

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.urls import reverse

try:
    from selenium import webdriver
    from selenium.common.exceptions import NoSuchElementException
    from selenium.webdriver.common.by import By
    from selenium.webdriver.firefox.options import Options
    from selenium.webdriver.support.wait import WebDriverWait

    HAS_SELENIUM = True
except ImportError:
    HAS_SELENIUM = False

HAS_GECKODRIVER = bool(shutil.which("geckodriver"))
SKIP_SELENIUM = bool(os.environ.get("RICHTEXT_LINK_SKIP_SELENIUM"))


def selenium_available():
    return HAS_SELENIUM and HAS_GECKODRIVER and not SKIP_SELENIUM


skip_unless_selenium = unittest.skipUnless(
    selenium_available(),
    "selenium/geckodriver not available (or RICHTEXT_LINK_SKIP_SELENIUM set)",
)


def get_firefox_binary():
    """
    The real firefox binary - /usr/bin/firefox is a shim on snap based
    ubuntus, which geckodriver refuses. Override with FIREFOX_BINARY.
    """
    binary = os.environ.get("FIREFOX_BINARY")
    if binary:
        return binary
    snap_binary = "/snap/firefox/current/usr/lib/firefox/firefox"
    if os.path.exists(snap_binary):
        return snap_binary
    return None


class SeleniumTestCase(StaticLiveServerTestCase):
    """
    A base test case for Selenium, providing helper methods for generating
    clients and logging in profiles.
    """

    username = "admin"
    password = "admin"

    def setUp(self):
        User.objects.create_superuser(self.username, "admin@bnzk.ch", self.password)
        options = Options()
        if getattr(settings, "HEADLESS_TESTING", True):
            options.add_argument("--headless")
        firefox_binary = get_firefox_binary()
        if firefox_binary:
            options.binary_location = firefox_binary
        self.webdriver = CustomWebDriver(options=options)

    def tearDown(self):
        self.webdriver.quit()

    def open(self, url):
        self.webdriver.get(f"{self.live_server_url}{url}")

    def login(self):
        self.open(reverse("admin:index"))
        self.webdriver.find_css("#id_username").send_keys(self.username)
        self.webdriver.find_css("#id_password").send_keys(self.password)
        self.webdriver.find_element(By.XPATH, '//input[@type="submit"]').click()
        self.webdriver.wait_for_css("body.dashboard")


if HAS_SELENIUM:

    class CustomWebDriver(webdriver.Firefox):
        """Our own WebDriver with some helpers added"""

        def find_css(self, css_selector):
            """Shortcut to find elements by CSS. Returns either a list or singleton"""
            elems = self.find_elements(By.CSS_SELECTOR, css_selector)
            found = len(elems)
            if found == 1:
                return elems[0]
            elif not elems:
                raise NoSuchElementException(css_selector)
            return elems

        def wait_for_css(self, css_selector, timeout=7):
            """Shortcut for WebDriverWait"""
            return WebDriverWait(self, timeout).until(
                lambda driver: driver.find_css(css_selector)
            )
