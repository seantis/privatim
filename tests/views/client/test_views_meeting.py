import pytest
from playwright.sync_api import Page, expect
from datetime import datetime, timedelta
import re
import transaction

from privatim.models import User, WorkingGroup, Meeting
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sedate import utcnow, to_timezone
from zoneinfo import ZoneInfo
from privatim.utils import fix_utc_to_local_time


def set_datetime_element(page: Page, selector: str, dt: datetime):
    """Sets the date and time on a datetime-local field using Playwright's fill method."""
    local_tz = ZoneInfo("Europe/Zurich")
    local_dt = dt.astimezone(local_tz)
    datetime_str = local_dt.strftime("%Y-%m-%dT%H:%M")

    script = """
        (args) => {
            const [selector, dateTimeString] = args;
            const element = document.querySelector(selector);
            if (!element) {
                console.error(`[Evaluate] Element not found for selector: ${selector}`);
                return { success: false, error: 'Element not found' };
            }
            try {
                // Ensure element is focused before setting value
                element.focus();
                // Set the value
                element.value = dateTimeString;
                // Dispatch events to mimic user input and trigger potential listeners
                element.dispatchEvent(new Event('input', { bubbles: true, cancelable: true }));
                element.dispatchEvent(new Event('change', { bubbles: true, cancelable: true }));
                // Optional: Dispatch blur if needed, but often focus moves automatically
                // element.dispatchEvent(new Event('blur', { bubbles: true, cancelable: true }));
                return { success: true, finalValue: element.value };
            } catch (error) {
                console.error(`[Evaluate] Error setting value for ${selector}:`, error);
                return { success: false, error: error.message, finalValue: element.value };
            }
        }
    """

    try:
        element = page.locator(selector)
        element.wait_for(state="visible", timeout=3000)
        result = page.evaluate(script, [selector, datetime_str])

        if not result or not result.get("success"):
            error_msg = (
                result.get("error", "Unknown error")
                if result
                else "Script execution failed"
            )
            raise Exception(
                f"Failed to set datetime via page.evaluate for '{selector}'. Error: {error_msg}"
            )

        expect(element).to_have_value(datetime_str)

    except Exception as e:
        safe_selector = re.sub(r"[^a-zA-Z0-9_-]", "_", selector)
        screenshot_path = f"playwright-fail-datetime-{safe_selector}.png"
        try:
            page.screenshot(path=screenshot_path, full_page=True)
            print(f"Screenshot saved to {screenshot_path}")
        except Exception as se:
            print(f"Failed to save screenshot: {se}")
        raise Exception(
            f"Failed to set datetime element '{selector}' to '{datetime_str}'. Original error: {e}"
        ) from e


def speichern(page):
    submit_button = page.locator('button[type="submit"]:has-text("Speichern")')
    submit_button.scroll_into_view_if_needed()
    submit_button.click()


@pytest.mark.browser
def test_edit_meeting_browser(page: Page, live_server_url, session) -> None:
    admin_user = User(
        email="test@example.org",
        first_name="Test",
        last_name="User",
    )
    admin_user.set_password("test")
    external_user = User(
        email="external@example.org",
        first_name="External",
        last_name="User",
    )
    external_user.set_password("test")
    session.add(external_user)
    session.add(admin_user)
    transaction.commit()

    page.goto(live_server_url + "/login")
    page.locator('input[name="email"]').fill("admin@example.org")
    page.locator('input[name="password"]').fill("test")

    page.locator('button[type="submit"]').click()
    page.wait_for_load_state("networkidle", timeout=10000)

    error_locator = page.locator(".alert.alert-danger")
    if error_locator.is_visible():
        error_text = error_locator.text_content()
        pytest.fail(f"Login failed. Error message found: {error_text}")

    expect(page).not_to_have_url(re.compile(r".*/login$"), timeout=5000)

    page.goto(live_server_url + "/working_groups/add")
    page.wait_for_load_state("networkidle", timeout=10000)  # Wait for page load

    group_name_input = page.locator('textarea[name="name"]')
    group_name = f"Browser Test Group {datetime.now().isoformat()}"
    group_name_input.fill(group_name)

    user_select_input = page.locator('input[id="users-ts-control"]')
    user_select_input.wait_for(state="visible", timeout=3000)
    user_select_input.click()
    user_select_input.fill("Admin User")
    admin_option = page.locator('.ts-dropdown-content .option:has-text("Admin User")')
    admin_option.wait_for(state="visible", timeout=3000)
    admin_option.click()

    user_select_input.fill("Test User")  # Start typing again
    test_option = page.locator('.ts-dropdown-content .option:has-text("Test User")')
    test_option.wait_for(state="visible", timeout=3000)
    test_option.click()
    speichern(page)

    # We are now in working groups overview page.
    # Click on the created working group:
    page.locator('a:has-text("Browser Test Group")').click()
    # new meeting:
    page.locator('a:has-text("Sitzung hinzufügen")').click()
    meeting_name = "Initial Browser Meeting"
    m_name = 'input[name="name"]'

    # Observe: We've resorted to JavaScript for this seemingly trivial task. 
    # Akin to deploying artillery against a mouse, we're merely setting the 
    # meeting title. Conventional approaches (element.fill) resulted in 
    # mysterious timeout issues, hence this elaborate solution.
    page.evaluate(f"""
        const el = document.querySelector('{m_name}');
        if (el) {{
            el.value = '{meeting_name}';
            el.dispatchEvent(new Event('input', {{ bubbles: true }}));
            el.dispatchEvent(new Event('change', {{ bubbles: true }}));
        }} else {{
            console.error(`[Evaluate] Element not found: {m_name}`);
        }}
    """)
    expect(page.locator(m_name)).to_have_value(meeting_name)
    meeting_time = utcnow() + timedelta(hours=1)
    set_datetime_element(page, 'input[name="time"]', meeting_time)

    # we will add this later. 
    # page.locator('.ts-dropdown-content .option:has-text("External User")').click()

    speichern(page)


def test_copy_agenda_items_without_description(client):
    client.login_admin()
    users = [
        User(email="max@example.org", first_name="Max", last_name="Müller"),
        User(email="alexa@example.org", first_name="Alexa", last_name="Troller"),
        User(email="kurt@example.org", first_name="Kurt", last_name="Huber"),
    ]
    for user in users:
        user.set_password("test")
        client.db.add(user)
    client.db.commit()

    working_group = WorkingGroup(name="Test Group", leader=users[0])
    working_group.users.extend(users)
    client.db.add(working_group)

    meeting_time = fix_utc_to_local_time(utcnow())

    # Create source meeting with agenda items
    src_meeting = Meeting(
        name="Source Meeting",
        time=meeting_time,
        attendees=users[:2],
        working_group=working_group,
    )
    client.db.add(src_meeting)
    client.db.commit()
    client.db.refresh(src_meeting)

    # Add agenda item to source meeting
    page = client.get(f"/meetings/{src_meeting.id}/add")
    page.form["title"] = "Agenda item"
    page.form["description"] = "description"
    page.form.submit().follow()

    # Create destination meeting (this will be our context)
    dest_meeting = Meeting(
        name="Destination Meeting",
        time=meeting_time,
        attendees=users[:2],
        working_group=working_group,
    )
    client.db.add(dest_meeting)
    client.db.commit()
    client.db.refresh(dest_meeting)

    # Copy agenda items from source to destination
    page = client.get(f"/meetings/{dest_meeting.id}/copy_agenda_item")
    page.form["copy_from"] = str(src_meeting.id)
    page.form["copy_description"] = False
    page.form.submit().follow()

    # Verify the agenda item was copied
    stmt = (
        select(Meeting)
        .options(selectinload(Meeting.agenda_items))
        .where(Meeting.id == dest_meeting.id)
    )
    dest_updated = client.db.scalars(stmt).unique().one()
    assert len(dest_updated.agenda_items) == 1
    assert dest_updated.agenda_items[0].title == "Agenda item"
    # Description wasn't copied
    assert dest_updated.agenda_items[0].description == ""
