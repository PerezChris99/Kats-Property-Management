"""Read-only real-browser smoke/role tests for the running local application.

The optional owner credentials must be provided by environment variables.
Never use production credentials or run against a public production URL.
"""
import os
import re
import pytest
from playwright.sync_api import sync_playwright, expect

BASE = os.environ.get("KATS_BASE_URL", "http://localhost:5173").rstrip("/")
if not (BASE.startswith("http://localhost:") or BASE.startswith("http://127.0.0.1:")):
    raise RuntimeError("Browser E2E is restricted to localhost; use an isolated local stack.")


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        yield browser
        browser.close()


@pytest.fixture()
def page(browser):
    context = browser.new_context(viewport={"width": 1365, "height": 768})
    page = context.new_page()
    yield page
    context.close()


def test_public_landing_and_login_link(page):
    page.goto(BASE + "/", wait_until="domcontentloaded")
    expect(page.get_by_role("heading", level=1)).to_contain_text("Manage your rentals")
    page.get_by_role("link", name="Sign in").click()
    expect(page).to_have_url(re.compile(r"/login$"))
    expect(page.get_by_role("heading", name="Sign in")).to_be_visible()


@pytest.mark.parametrize("viewport", [
    {"width": 360, "height": 780},
    {"width": 768, "height": 1024},
    {"width": 1440, "height": 900},
])
def test_responsive_landing_has_no_horizontal_overflow(browser, viewport):
    context = browser.new_context(viewport=viewport)
    page = context.new_page()
    try:
        page.goto(BASE + "/", wait_until="domcontentloaded")
        expect(page.get_by_role("heading", level=1)).to_be_visible()
        assert page.evaluate(
            "() => document.documentElement.scrollWidth <= window.innerWidth + 2"
        ), f"Landing page overflow at {viewport}"
    finally:
        context.close()


@pytest.mark.parametrize("route", [
    "/dashboard", "/properties", "/invoices", "/audit",
    "/documents", "/disputes", "/preventive-maintenance",
])
def test_anonymous_users_redirect_from_private_portals(page, route):
    page.goto(BASE + route, wait_until="domcontentloaded")
    expect(page).to_have_url(re.compile(r"/login$"))
    expect(page.get_by_role("heading", name="Sign in")).to_be_visible()


def test_public_api_and_sensitive_headers(page):
    ready = page.request.get(BASE + "/readyz")
    assert ready.status == 200, ready.text()
    private = page.request.get(BASE + "/api/v1/properties")
    assert private.status == 401, private.text()
    assert "no-store" in private.headers.get("cache-control", "")
    assert private.headers.get("x-content-type-options") == "nosniff"
    assert private.headers.get("x-frame-options") == "DENY"
    assert private.headers.get("content-security-policy")


def test_failed_login_does_not_open_workspace(page):
    page.goto(BASE + "/login")
    page.get_by_label("Email", exact=True).fill("unknown@example.invalid")
    page.get_by_label("Password", exact=True).fill("incorrect-password")
    page.get_by_role("button", name="Continue").click()
    expect(page.get_by_role("alert")).to_be_visible()
    expect(page).to_have_url(re.compile(r"/login$"))


def test_owner_read_only_portal_navigation(page):
    email = os.environ.get("KATS_E2E_OWNER_EMAIL")
    password = os.environ.get("KATS_E2E_OWNER_PASSWORD")
    if not email or not password:
        pytest.skip("Set KATS_E2E_OWNER_EMAIL and KATS_E2E_OWNER_PASSWORD for owner browser coverage")
    page.goto(BASE + "/login")
    page.get_by_label("Email", exact=True).fill(email)
    page.get_by_label("Password", exact=True).fill(password)
    code = os.environ.get("KATS_E2E_OWNER_TOTP")
    if code:
        page.get_by_label("Authenticator code (if enabled)").fill(code)
    page.get_by_role("button", name="Continue").click()
    expect(page).to_have_url(re.compile(r"/dashboard$"), timeout=15000)
    for route in ("/dashboard", "/properties", "/invoices", "/maintenance",
                  "/utilities", "/disputes", "/preventive-maintenance"):
        page.goto(BASE + route, wait_until="domcontentloaded")
        expect(page.locator("main.portal-content")).to_be_visible()
