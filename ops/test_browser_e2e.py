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
    expect(page.get_by_role("heading", level=1)).to_contain_text("Manage property")
    page.get_by_role("navigation", name="Main navigation").get_by_role("link", name="Sign in").click()
    expect(page).to_have_url(re.compile(r"/login$"))
    expect(page.get_by_role("heading", name="Sign in to your account")).to_be_visible()


@pytest.mark.parametrize("viewport", [
    {"width": 360, "height": 780},
    {"width": 390, "height": 844},
    {"width": 768, "height": 1024},
    {"width": 1024, "height": 768},
    {"width": 1440, "height": 900},
])
@pytest.mark.parametrize("route", [
    "/", "/features", "/about", "/request-access", "/login", "/privacy",
])
def test_public_pages_have_no_horizontal_overflow(browser, viewport, route):
    context = browser.new_context(viewport=viewport, reduced_motion="reduce")
    page = context.new_page()
    try:
        page.goto(BASE + route, wait_until="domcontentloaded")
        expect(page.locator("main")).to_be_visible()
        result = page.evaluate("""() => {
            const width = document.documentElement.clientWidth;
            const selectors = [
              '.pm-hero-panel', '.pm-feature-card', '.pm-chart-panel',
              '.pm-contact-form', '.pm-contact-form input:not([type="checkbox"]):not(.pm-honeypot)',
              '.pm-contact-form select', '.pm-contact-form textarea',
              '.pm-login-layout', '.pm-login-card', '.pm-legal-body',
              '.pm-step-grid article', '.pm-trust-grid article',
              '.pm-footer-body'
            ];
            const escaped = selectors.flatMap(selector =>
              [...document.querySelectorAll(selector)].filter(el => {
                const box = el.getBoundingClientRect();
                const style = window.getComputedStyle(el);
                return style.display !== 'none' && box.width > 0 &&
                  (box.right > width + 2 || box.left < -2 || box.width > width + 2);
              }).map(el => ({
                selector, left: Math.round(el.getBoundingClientRect().left),
                right: Math.round(el.getBoundingClientRect().right), width
              }))
            );
            return {scrollWidth: document.documentElement.scrollWidth, width, escaped};
        }""")
        assert result["scrollWidth"] <= result["width"] + 2, (
            f"Page has horizontal scroll at {route} {viewport}: {result}"
        )
        assert not result["escaped"], f"Form/card overflows {route} {viewport}: {result['escaped']}"
    finally:
        context.close()


@pytest.mark.parametrize("route", [
    "/dashboard", "/properties", "/invoices", "/audit",
    "/documents", "/disputes", "/preventive-maintenance",
])
def test_anonymous_users_redirect_from_private_portals(page, route):
    page.goto(BASE + route, wait_until="domcontentloaded")
    expect(page).to_have_url(re.compile(r"/login$"))
    expect(page.get_by_role("heading", name="Sign in to your account")).to_be_visible()


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
    page.get_by_label("Email address", exact=True).fill("unknown@example.invalid")
    page.get_by_label("Password", exact=True).fill("incorrect-password")
    page.get_by_role("button", name="Sign in securely").click()
    expect(page.get_by_role("alert")).to_be_visible()
    expect(page).to_have_url(re.compile(r"/login$"))



STAFF_ROUTES = [
    "dashboard", "properties", "buildings", "floors", "rooms",
    "room-placement", "portfolio-editor", "tenants", "leases", "proration",
    "invoices", "payments", "utilities", "maintenance",
    "preventive-maintenance", "disputes", "expenses", "expense-approvals",
    "reports", "trends", "statements", "receipts", "mobile-money",
    "efris", "inspections", "renewals", "deposits", "work-orders",
    "documents", "notifications", "privacy-requests", "security",
]
ADMIN_ROUTES = [
    "settings", "users", "invitations", "permissions", "legal", "audit", "inquiries",
]
TENANT_ROUTES = [
    "dashboard", "invoices", "payments", "utilities", "statements",
    "receipts", "deposits", "maintenance", "disputes", "inspections",
    "documents", "mobile-money", "notifications", "privacy-requests", "security",
]
CARETAKER_ROUTES = [
    "dashboard", "rooms", "payments", "utilities", "maintenance",
    "preventive-maintenance", "work-orders", "inspections", "documents",
    "notifications", "privacy-requests", "security", "receipts",
]

@pytest.mark.parametrize("role", [
    "OWNER", "SUPER_ADMIN", "MANAGER", "ACCOUNTANT", "CARETAKER", "TENANT",
])
def test_read_only_authenticated_role_portals(page, role):
    email = os.environ.get(f"KATS_E2E_{role}_EMAIL")
    password = os.environ.get(f"KATS_E2E_{role}_PASSWORD")
    if not email or not password:
        pytest.skip(f"Provide disposable local {role} E2E credentials to test this role")
    page.goto(BASE + "/login")
    page.get_by_label("Email address", exact=True).fill(email)
    page.get_by_label("Password", exact=True).fill(password)
    code = os.environ.get(f"KATS_E2E_{role}_TOTP")
    if code:
        page.get_by_label("Authenticator code (if enabled)").fill(code)
    page.get_by_role("button", name="Sign in securely").click()
    expect(page).to_have_url(re.compile(r"/dashboard$"), timeout=15000)
    expect(page.locator("main.portal-content")).to_be_visible()
    auth = page.request.get(BASE + "/api/v1/auth/me")
    assert auth.status == 200, auth.text()
    assert auth.json()["user"]["role"] == role
    if role in ("OWNER", "SUPER_ADMIN"):
        routes = STAFF_ROUTES + ADMIN_ROUTES + ["assignments"]
    elif role == "MANAGER":
        routes = STAFF_ROUTES + ["assignments"]
    elif role == "ACCOUNTANT":
        routes = STAFF_ROUTES
    elif role == "CARETAKER":
        routes = CARETAKER_ROUTES
    else:
        routes = TENANT_ROUTES
    if role in ("CARETAKER", "TENANT"):
        # Frontend hiding a page is not equivalent to denying backend access.
        forbidden = page.request.get(BASE + "/api/v1/audit")
        assert forbidden.status == 403, forbidden.text()
    runtime_errors = []
    page.on("pageerror", lambda error: runtime_errors.append(str(error)))
    for route in routes:
        page.goto(BASE + "/" + route, wait_until="domcontentloaded")
        expect(page.locator("main.portal-content")).to_be_visible()
        # Allow lazy chunks and their initial data requests to settle.
        page.wait_for_timeout(100)
        assert not runtime_errors, f"{role} /{route} browser exception: {runtime_errors}"


def test_access_request_is_submitted_to_backend_without_auto_account(page):
    page.goto(BASE + "/request-access")
    page.get_by_label("Full name").fill("Test Property Manager")
    page.get_by_label("Email address").fill("request-test@example.invalid")
    page.get_by_role("combobox", name="Your role").select_option(label="Manager")
    page.get_by_label("Why do you need access?").fill("I manage our rental portfolio in Kampala.")
    page.get_by_label(re.compile(r"I agree to the handling")).check()
    page.get_by_role("button", name="Submit request").click()
    expect(page.get_by_role("status")).to_contain_text("Request submitted for administrator review")
    expect(page).to_have_url(re.compile(r"/request-access$"))


def test_hero_depth_moves_on_scroll_and_closing_cta_is_unboxed(browser):
    """Real scroll motion and actionable closing link, without a floating card."""
    context = browser.new_context(
        viewport={"width": 1365, "height": 850}, reduced_motion="no-preference"
    )
    page = context.new_page()
    try:
        page.goto(BASE + "/", wait_until="domcontentloaded")
        hero = page.locator(".pm-hero")
        expect(hero.locator(".pm-hero-copy")).to_be_visible()
        assert hero.locator(".pm-hero-panel").count() == 0
        page.evaluate("window.scrollTo(0, 320)")
        page.wait_for_function("""() => {
            const hero = document.querySelector('.pm-hero');
            return Number.parseFloat(
                getComputedStyle(hero).getPropertyValue('--pm-parallax-y')
            ) > 12;
        }""", timeout=6000)
        endcap = page.get_by_role("region", name="Get started with KATS")
        expect(endcap).to_be_visible()
        assert endcap.locator(".pm-glass, .pm-hero-panel, .pm-access-line").count() == 0
        expect(endcap.get_by_role("link", name="Request access")).to_have_attribute(
            "href", "/request-access"
        )
        assert endcap.evaluate(
            "el => getComputedStyle(el).backgroundColor"
        ) == "rgb(237, 245, 250)"
    finally:
        context.close()


def test_hero_respects_reduced_motion(browser):
    context = browser.new_context(
        viewport={"width": 1280, "height": 800}, reduced_motion="reduce"
    )
    page = context.new_page()
    try:
        page.goto(BASE + "/", wait_until="domcontentloaded")
        page.evaluate("window.scrollTo(0, 260)")
        assert page.locator(".pm-hero-images").evaluate(
            "el => getComputedStyle(el).transform"
        ) == "none"
    finally:
        context.close()


@pytest.mark.parametrize("legacy,section", [
    ("/features", "capabilities"),
    ("/how-it-works", "workflow"),
    ("/about", "about"),
])
def test_legacy_marketing_urls_redirect_to_home_sections(page, legacy, section):
    page.goto(BASE + legacy, wait_until="domcontentloaded")
    expect(page).to_have_url(re.compile(r"/#" + re.escape(section) + r"$"))
    expect(page.locator("#" + section)).to_be_visible()
    expect(page.get_by_role("heading", level=1)).to_contain_text("Manage property")


def test_public_navigation_is_management_first(page):
    page.goto(BASE + "/", wait_until="domcontentloaded")
    nav = page.get_by_role("navigation", name="Main navigation")
    expect(nav.get_by_role("link", name="Home")).to_have_count(1)
    expect(nav.get_by_role("link", name="Request access")).to_have_count(1)
    expect(nav.get_by_role("link", name="Sign in")).to_have_count(1)
    for old in ("Features", "How it works", "About"):
        expect(nav.get_by_role("link", name=old, exact=True)).to_have_count(0)
    expect(page.locator("#capabilities")).to_be_visible()
    expect(page.locator("#workflow")).to_be_visible()
    expect(page.locator("#about")).to_be_visible()
    expect(page.locator(".pm-faq")).to_have_count(0)
    expect(page.locator(".pm-problem")).to_have_count(0)
    expect(page.locator(".pm-endcap")).to_have_count(1)


def test_house_return_to_top_and_developer_attribution(page):
    page.goto(BASE + "/", wait_until="domcontentloaded")
    footer = page.locator("footer.pm-footer")
    credit = footer.get_by_role("link", name="Developed by Kweezi Perez Christopher")
    expect(credit).to_have_attribute("href", "https://kweeziperez.com")
    expect(credit).to_have_attribute("target", "_blank")
    assert footer.locator(".pm-credits").count() == 0
    assert "Photo credits & license" not in footer.inner_text()
    page.evaluate("window.scrollTo({top: 1200, behavior: 'instant'})")
    home = page.get_by_role("button", name="Return to top")
    expect(home).to_be_visible(timeout=6000)
    home.click()
    page.wait_for_function("window.scrollY < 30", timeout=8000)


def test_uganda_legal_context_and_media_attribution_are_available(page):
    page.goto(BASE + "/refund", wait_until="domcontentloaded")
    expect(page.get_by_role("heading", name="Relevant statutory guidance")).to_be_visible()
    expect(page.get_by_text("Security deposits", exact=True)).to_be_visible()
    expect(page.get_by_role("link", name=re.compile("Landlord and Tenant Act, 2022"))).to_have_attribute("target", "_blank")
    page.get_by_role("link", name="Image licenses").click()
    expect(page).to_have_url(re.compile(r"/image-attributions$"))
    expect(page.get_by_role("heading", name="Image sources & licenses")).to_be_visible()
    assert page.get_by_role("link", name="Creative Commons Attribution-ShareAlike 4.0").count() == 5


def test_first_hero_image_is_preloaded_and_typography_is_editorial(page):
    page.goto(BASE + "/", wait_until="domcontentloaded")
    assert page.locator('link[rel="preload"][as="image"][fetchpriority="high"]').count() == 1
    expect(page.locator(".pm-hero-images .pm-slide")).to_have_count(5)
    font = page.locator(".pm-hero h1").evaluate("el => getComputedStyle(el).fontFamily")
    assert "Newsreader" in font
