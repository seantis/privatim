from playwright.sync_api import Page, expect
import pytest

# Mark all tests in this module as browser tests
pytestmark = pytest.mark.browser


def test_login_page_loads(page: Page, live_server_url: str) -> None:
    """
    Test that the login page loads correctly.
    """
    login_url = live_server_url + '/login'
    page.goto(login_url)
    expect(page).to_have_title(r"Austauschplattform privatim")

    # Check for essential form elements
    expect(page.locator('input[name="email"]')).to_be_visible()
    expect(page.locator('input[name="password"]')).to_be_visible()
    expect(page.locator('button[type="submit"]')).to_be_visible()


def test_root_page_loads(page: Page, live_server_url: str) -> None:
    response = page.goto(live_server_url + '/')
    assert response is not None and response.ok
