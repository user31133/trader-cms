import os
import pytest
from playwright.sync_api import Page, BrowserContext

CMS_URL = os.environ.get("CMS_URL", "http://localhost:8000")
TEST_EMAIL = "test@test.com"
TEST_PASSWORD = "testpassword123"


def do_login(page: Page) -> None:
    page.goto(f"{CMS_URL}/login")
    page.fill('input[name=email]', TEST_EMAIL)
    page.fill('input[name=password]', TEST_PASSWORD)
    page.click('button[type=submit]')
    page.wait_for_url(f"**/products", timeout=15_000)


@pytest.fixture
def cms_url() -> str:
    return CMS_URL


@pytest.fixture
def logged_in_page(page: Page) -> Page:
    """Page fixture already authenticated as the test trader."""
    do_login(page)
    return page
