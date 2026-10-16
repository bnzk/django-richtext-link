"""
The editors are sanitizers too: a strict Quill formats whitelist, a CKEditor
plugin setup or an own editor build can strip the data-richtext-link marker
(or legacy format links) the moment content loads - the python startup checks
cannot see that, only a real browser can. This command renders every
RICHTEXT_LINK_CONFIGS editor on a probe page with probe links (current + the
legacy formats while RICHTEXT_LINK_LEGACY_CHECK is on), lets the widget's own
round trip check run in headless firefox, and fails when link data is lost.
Run it in CI / predeploy, next to `manage.py check --deploy`.
"""
import contextlib
import threading
from wsgiref.simple_server import WSGIRequestHandler, make_server

from django import forms
from django.core.management.base import BaseCommand, CommandError

from richtext_link import conf
from richtext_link.checks import LEGACY_PROBE_HTML, PROBE_HTML
from richtext_link.widgets import RichtextWidget

ALL_CHECKED_JS = """
var areas = document.querySelectorAll("textarea[data-richtext-link-widget]");
return Array.prototype.every.call(areas, function (t) {
  return t.dataset.richtextLinkChecked;
});
"""

RESULTS_JS = """
var areas = document.querySelectorAll("textarea[data-richtext-link-widget]");
return Array.prototype.map.call(areas, function (t) {
  return [t.id, t.dataset.richtextLinkChecked];
});
"""


class QuietHandler(WSGIRequestHandler):
    def log_message(self, *args):
        pass


def build_probe_page():
    probe_content = PROBE_HTML
    if conf.get_legacy_check():
        probe_content += "".join(LEGACY_PROBE_HTML.values())
    media = forms.Media()
    rows = []
    skipped = []
    for name, config in conf.get_configs().items():
        if (
            isinstance(config, dict)
            and config.get("editor") == "ckeditor5"
            and not config.get("assets")
        ):
            # bring your own build: nothing this page could load
            skipped.append(name)
            continue
        widget = RichtextWidget(config_name=name)
        media += widget.media
        rows.append(
            f"<h2>{name}</h2>"
            + widget.render(
                f"probe_{name}", probe_content, attrs={"id": f"id_probe_{name}"}
            )
        )
    page = (
        '<!doctype html><html><head><meta charset="utf-8">'
        f"<title>richtext-link editor check</title>{media}</head>"
        f"<body>{''.join(rows)}</body></html>"
    )
    return page, skipped


class Command(BaseCommand):
    help = (
        "Round trip probe links (current + legacy formats) through every "
        "configured editor in headless firefox - fails when an editor "
        "configuration loses link data."
    )

    def add_arguments(self, parser):
        parser.add_argument("--timeout", type=int, default=20)
        parser.add_argument("--visible", action="store_true")

    def handle(self, *args, **options):
        page, skipped = build_probe_page()
        server = _serve(page)
        driver = _launch_firefox(visible=options["visible"])
        try:
            results = _collect_results(driver, server, options["timeout"])
        finally:
            with contextlib.suppress(Exception):
                driver.quit()
            server.shutdown()
        self._report(results, skipped)

    def _report(self, results, skipped):
        for name in skipped:
            self.stdout.write(
                f"skipped: {name} (ckeditor5 without the assets config - "
                f"bring your own build cannot be loaded here)"
            )
        failed = []
        for textarea_id, status in results:
            config_name = textarea_id.replace("id_probe_", "", 1)
            self.stdout.write(f"{config_name}: {status}")
            if status != "ok":
                failed.append(config_name)
        if failed:
            msg = (
                f"link data lost (or editor failed to initialize) for "
                f"config(s): {', '.join(failed)} - these configurations "
                f"would destroy links on save."
            )
            raise CommandError(msg)
        self.stdout.write(self.style.SUCCESS("all editor round trips ok"))


def _serve(page):
    try:
        from django.contrib.staticfiles.handlers import StaticFilesHandler
    except ImportError as exc:
        msg = "django.contrib.staticfiles is required"
        raise CommandError(msg) from exc

    body = page.encode("utf-8")

    def probe_app(environ, start_response):
        start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
        return [body]

    server = make_server(
        "127.0.0.1", 0, StaticFilesHandler(probe_app), handler_class=QuietHandler
    )
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def _launch_firefox(*, visible):
    try:
        from selenium import webdriver
        from selenium.webdriver.firefox.options import Options
    except ImportError as exc:
        msg = "selenium is required: pip install selenium (+ geckodriver)"
        raise CommandError(msg) from exc

    from richtext_link.tests.utils.selenium_utils import get_firefox_binary

    browser_options = Options()
    if not visible:
        browser_options.add_argument("--headless")
    firefox_binary = get_firefox_binary()
    if firefox_binary:
        browser_options.binary_location = firefox_binary
    return webdriver.Firefox(options=browser_options)


def _collect_results(driver, server, timeout):
    from selenium.common.exceptions import TimeoutException
    from selenium.webdriver.support.wait import WebDriverWait

    try:
        driver.get(f"http://127.0.0.1:{server.server_address[1]}/")
        WebDriverWait(driver, timeout).until(lambda d: d.execute_script(ALL_CHECKED_JS))
        return driver.execute_script(RESULTS_JS)
    except TimeoutException as exc:
        msg = (
            "timed out waiting for the editor round trip checks - an "
            "editor never initialized (missing assets/js errors? run "
            "with --visible to look at the probe page)."
        )
        raise CommandError(msg) from exc
