import pytest
from playwright.sync_api import Page, expect
from datetime import datetime, timedelta
import re

from privatim.models import User, WorkingGroup, Meeting
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sedate import utcnow
from privatim.utils import fix_utc_to_local_time


@pytest.mark.browser
def test_edit_meeting_browser(page: Page, live_server_url: str) -> None:
    page.goto(live_server_url + '/login')
    page.locator('input[name="email"]').fill('admin@example.org')
    page.locator('input[name="password"]').fill('test')

    page.locator('button[type="submit"]').click()
    page.wait_for_load_state('networkidle', timeout=10000)

    error_locator = page.locator('.alert.alert-danger')
    if error_locator.is_visible():
        error_text = error_locator.text_content()
        pytest.fail(f"Login failed. Error message found: {error_text}")

    expect(page).not_to_have_url(re.compile(r'.*/login$'), timeout=5000)

    page.goto(live_server_url + '/working_groups/add')
    page.wait_for_load_state('networkidle', timeout=10000) # Wait for page load

    # Wait for the name input and fill it
    group_name_input = page.locator('input[name="name"]')
    group_name_input.wait_for(state='visible', timeout=5000) # Wait for element
    group_name_input.wait_for(state='enabled', timeout=5000) # Wait for element to be enabled
    group_name = f'Browser Test Group {datetime.now().isoformat()}'
    group_name_input.fill(group_name)

    # Select users using Tom Select
    # Wait for the Tom Select input, click it, and fill
    user_select_input = page.locator('input[id="users-ts-control"]')
    user_select_input.wait_for(state='visible', timeout=5000)
    user_select_input.click()
    # Select 'Admin User' (adjust name if necessary)
    user_select_input.fill('Admin User') # Start typing to filter
    admin_option = page.locator('.ts-dropdown-content .option:has-text("Admin User")')
    admin_option.wait_for(state='visible', timeout=2000) # Wait for option to appear
    admin_option.click()

    # Select 'Test User' (adjust name if necessary, ensure this user exists)
    user_select_input.fill('Test User') # Start typing again
    test_option = page.locator('.ts-dropdown-content .option:has-text("Test User")')
    test_option.wait_for(state='visible', timeout=2000) # Wait for option to appear
    test_option.click()

    # Click outside the dropdown to close it (optional, good practice)
    page.locator('h1').click() # Click the header or another element

    page.locator('button[type="submit"]:has-text("Speichern")').click() # Adjust button text if needed

    # Wait for redirect and extract group ID
    expect(page).to_have_url(re.compile(r'.*/working_groups/[\w-]+$'))
    group_id_match = re.search(r'/working_groups/([\w-]+)', page.url)
    assert group_id_match, "Could not extract working group ID from URL"
    group_id = group_id_match.group(1)

    # 3. Create Meeting
    page.goto(live_server_url + f'/working_groups/{group_id}/meetings/add')
    initial_meeting_name = f'Initial Browser Meeting {datetime.now().isoformat()}'
    page.locator('input[name="name"]').fill(initial_meeting_name)
    page.locator('input[name="name"]').fill(initial_meeting_name)
    page.locator('button[type="submit"]:has-text("Speichern")').click()

    # Wait for redirect and extract meeting ID
    expect(page).to_have_url(re.compile(r'.*/meetings/[\w-]+$'))
    meeting_id_match = re.search(r'/meetings/([\w-]+)', page.url)
    assert meeting_id_match, "Could not extract meeting ID from URL"
    meeting_id = meeting_id_match.group(1)
    expect(page.locator('h1')).to_contain_text(initial_meeting_name) # Verify creation

    # 4. Navigate to Edit Meeting
    page.goto(live_server_url + f'/meetings/{meeting_id}/edit')
    expect(page.locator('h1')).to_contain_text('Sitzung bearbeiten') # Or 'Edit meeting'

    # 5. Edit Name
    updated_meeting_name = f'Updated Browser Meeting {datetime.now().isoformat()}'
    name_input = page.locator('input[name="name"]')
    name_input.clear() # Clear existing value
    name_input.fill(updated_meeting_name)

    # 6. Submit
    page.locator('button[type="submit"]:has-text("Speichern")').click()

    # 7. Assert
    # Should redirect back to the meeting view page
    expect(page).to_have_url(live_server_url + f'/meetings/{meeting_id}')
    # Check if the updated name is displayed prominently (e.g., in h1)
    expect(page.locator('h1')).to_contain_text(updated_meeting_name)
    # Optionally, check for a success flash message if applicable
    # expect(page.locator('.alert-success')).to_contain_text('Meeting updated') # Adjust selector/text


def test_copy_agenda_items_without_description(client):
    client.login_admin()
    users = [
        User(email='max@example.org', first_name='Max', last_name='Müller'),
        User(
            email='alexa@example.org',
            first_name='Alexa',
            last_name='Troller'
        ),
        User(email='kurt@example.org', first_name='Kurt', last_name='Huber'),
    ]
    for user in users:
        user.set_password('test')
        client.db.add(user)
    client.db.commit()

    working_group = WorkingGroup(name='Test Group', leader=users[0])
    working_group.users.extend(users)
    client.db.add(working_group)

    meeting_time = fix_utc_to_local_time(utcnow())

    # Create source meeting with agenda items
    src_meeting = Meeting(
        name='Source Meeting',
        time=meeting_time,
        attendees=users[:2],
        working_group=working_group,
    )
    client.db.add(src_meeting)
    client.db.commit()
    client.db.refresh(src_meeting)

    # Add agenda item to source meeting
    page = client.get(f'/meetings/{src_meeting.id}/add')
    page.form['title'] = 'Agenda item'
    page.form['description'] = 'description'
    page.form.submit().follow()

    # Create destination meeting (this will be our context)
    dest_meeting = Meeting(
        name='Destination Meeting',
        time=meeting_time,
        attendees=users[:2],
        working_group=working_group,
    )
    client.db.add(dest_meeting)
    client.db.commit()
    client.db.refresh(dest_meeting)

    # Copy agenda items from source to destination
    page = client.get(f'/meetings/{dest_meeting.id}/copy_agenda_item')
    page.form['copy_from'] = str(src_meeting.id)
    page.form['copy_description'] = False
    page.form.submit().follow()

    # Verify the agenda item was copied
    stmt = (
        select(Meeting)
        .options(selectinload(Meeting.agenda_items))
        .where(Meeting.id == dest_meeting.id)
    )
    dest_updated = client.db.scalars(stmt).unique().one()
    assert len(dest_updated.agenda_items) == 1
    assert dest_updated.agenda_items[0].title == 'Agenda item'
    # Description wasn't copied
    assert dest_updated.agenda_items[0].description == ''
