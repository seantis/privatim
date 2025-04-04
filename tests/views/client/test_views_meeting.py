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
    """ Sets the date and time on a datetime-local field using Playwright's fill method. """
    # Format datetime for datetime-local input (YYYY-MM-DDTHH:MM)
    # Ensure the datetime is in the local timezone expected by the browser/input
    # Using a common timezone like Zurich as an example. Adjust if needed.
    local_tz = ZoneInfo('Europe/Zurich')
    local_dt = dt.astimezone(local_tz)
    datetime_str = local_dt.strftime('%Y-%m-%dT%H:%M')

    # Format date and time parts
    local_tz = ZoneInfo('Europe/Zurich') # Ensure consistent timezone
    local_dt = dt.astimezone(local_tz)
    year = local_dt.strftime('%Y')
    month = local_dt.strftime('%m')
    day = local_dt.strftime('%d')
    hour = local_dt.strftime('%H')
    minute = local_dt.strftime('%M')

    print(f"Attempting to set datetime for selector '{selector}' using key presses: {year}-{month}-{day}T{hour}:{minute}")

    try:
        element = page.locator(selector)
        breakpoint()
        element.scroll_into_view_if_needed()
        element.click() # Focus the element

        # Simulate typing the date and time components
        # This sequence might need adjustment based on browser behavior
        # Using element.type() might be more reliable for sequences than press() for digits
        # element.type(year, delay=50) # Add small delay if needed
        # element.press('ArrowRight') # Or 'Tab'
        # element.type(month, delay=50)
        # element.press('ArrowRight') # Or 'Tab'
        # element.type(day, delay=50)
        # element.press('ArrowRight') # Or 'Tab'
        # element.type(hour, delay=50)
        # # element.press(':') # Colon might be automatic or require specific key
        # element.type(minute, delay=50)
        # element.press('Tab') # Move focus away to trigger change events

        # Alternative using fill for parts - might be more robust than individual presses
        element.fill(f'{year}-{month}-{day}')
        element.press('Tab') # Navigate to time part
        element.type(f'{hour}:{minute}') # Type time part
        element.press('Tab') # Tab away to confirm


        # Verification step (optional but recommended)
        # Wait a moment for potential JS updates
        page.wait_for_timeout(100) # Small pause
        current_value = element.input_value()
        expected_value_str = local_dt.strftime('%Y-%m-%dT%H:%M')
        print(f"Value after key presses for '{selector}': '{current_value}' (Expected: '{expected_value_str}')")
        if current_value != expected_value_str:
             # If fill didn't work, try press sequences (more granular)
             print("Fill approach failed, trying individual key presses...")
             element.click() # Re-focus
             element.press_sequentially(year, delay=20)
             element.press('ArrowRight') # Or 'Tab'
             element.press_sequentially(month, delay=20)
             element.press('ArrowRight') # Or 'Tab'
             element.press_sequentially(day, delay=20)
             element.press('ArrowRight') # Or 'Tab' - Move to time section
             element.press_sequentially(hour, delay=20)
             # element.press(':') # Often not needed, browser handles separator
             element.press('ArrowRight') # Or ':' depending on browser
             element.press_sequentially(minute, delay=20)
             element.press('Tab') # Tab away

             page.wait_for_timeout(100) # Small pause again
             current_value = element.input_value()
             print(f"Value after individual key presses for '{selector}': '{current_value}'")
             if current_value != expected_value_str:
                 print(f"Warning: Setting datetime via key presses for '{selector}' might have failed. Final value: '{current_value}'")
                 # raise Exception(f"Failed to set datetime element '{selector}' using key presses. Expected '{expected_value_str}', got '{current_value}'")


        print(f"Successfully attempted to set datetime for selector '{selector}' using key presses.")

    except Exception as e:
        print(f"Error setting datetime for selector '{selector}' using key presses: {e}")
        raise Exception(f"Failed to set datetime element with selector '{selector}' using key presses.") from e


def speichern(page):
    submit_button = page.locator('button[type="submit"]:has-text("Speichern")')
    submit_button.scroll_into_view_if_needed() # Explicitly scroll
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


    # wer are now in working groups overview page.
    # click on the created working group:
    page.locator('a:has-text("Browser Test Group")').click()
    # new meeting:
    page.locator('a:has-text("Sitzung hinzufügen")').click()
    meeting_name = f"Initial Browser Meeting {datetime.now().isoformat()}"
    page.locator('input[name="name"]').fill(meeting_name)

    # Set the meeting time using the helper function
    meeting_time = utcnow() + timedelta(hours=2) # Set time 2 hours from now
    set_datetime_element(page, 'input[name="time"]', meeting_time)

    # First add no explicit attenees.
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
