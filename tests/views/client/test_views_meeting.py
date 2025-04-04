import pytest
from playwright.sync_api import Page, expect
from datetime import datetime, timedelta
import re
import transaction

from privatim.models import User, WorkingGroup, Meeting
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sedate import utcnow
from privatim.utils import fix_utc_to_local_time


@pytest.mark.browser
def test_edit_meeting_browser(page: Page, live_server_url, session) -> None:

    admin_user = User(
        email="test@example.org",
        first_name="Test",
        last_name="User",
    )
    admin_user.set_password("test")
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

    page.locator(
        'button[type="submit"]:has-text("Speichern")'
    ).click()
    # wer are now in working groups overview page.
    # click on the created working group:
    page.locator('a:has-text("Browser Test Group")').click()
    page.locator('a:has-text("Sitzung hinzufügen")').click()

    initial_meeting_name = f"Initial Browser Meeting {datetime.now().isoformat()}"
    page.locator('input[name="name"]').fill(initial_meeting_name)

    # Add attendees - Working group members are added by default,
    # but we can explicitly add them here if needed or add others.
    # For this test, let's ensure the default behaviour works and submit.
    # If we needed to add *additional* users not in the group:
    # attendee_select_input = page.locator('input[id="attendees-ts-control"]')
    # attendee_select_input.wait_for(state="visible", timeout=3000)
    # attendee_select_input.click()
    # attendee_select_input.fill("Some Other User") # Assuming another user exists
    # other_user_option = page.locator('.ts-dropdown-content .option:has-text("Some Other User")')
    # other_user_option.wait_for(state="visible", timeout=3000)
    # other_user_option.click()

    page.locator(
        'button[type="submit"]:has-text("Speichern")'
    ).click()
    page.wait_for_load_state("networkidle", timeout=10000)

    # Verify we are on the meeting page and the attendees are listed
    expect(page.locator('.generic-user-list-container')).to_contain_text('Attendees:')
    expect(page.locator('.generic-user-list li:has-text("Admin User")')).to_be_visible()
    expect(page.locator('.generic-user-list li:has-text("Test User")')).to_be_visible()

    # Now, let's test editing the meeting - e.g., change the name
    page.locator('a[data-bs-toggle="dropdown"]:has(.bi-three-dots-vertical)').click()
    page.locator('a.dropdown-item:has-text("Edit")').click()
    page.wait_for_load_state("networkidle", timeout=10000)

    edited_meeting_name = f"Edited Browser Meeting {datetime.now().isoformat()}"
    page.locator('input[name="name"]').fill(edited_meeting_name)
    page.locator(
        'button[type="submit"]:has-text("Speichern")'
    ).click()
    page.wait_for_load_state("networkidle", timeout=10000)

    # Verify the name change on the meeting view page
    expect(page.locator('h1')).to_contain_text(edited_meeting_name)



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
