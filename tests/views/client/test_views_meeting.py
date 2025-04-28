import pytest
from playwright.sync_api import Page, expect
from datetime import datetime, timedelta
import re
import transaction

from privatim.models import User, WorkingGroup, Meeting
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sedate import utcnow
from zoneinfo import ZoneInfo
from privatim.utils import fix_utc_to_local_time


def set_datetime_element(page: Page, selector: str, dt: datetime):
    """Sets the date and time on a datetime-local field using Playwright's fill
    method."""
    local_tz = ZoneInfo("Europe/Zurich")
    local_dt = dt.astimezone(local_tz)
    datetime_str = local_dt.strftime("%Y-%m-%dT%H:%M")

    script = """
        (args) => {
            const [selector, dateTimeString] = args;
            const element = document.querySelector(selector);
            if (!element) {
                return { success: false, error: 'Element not found' };
            }
            try {
                // Ensure element is focused before setting value
                element.focus();
                // Set the value
                element.value = dateTimeString;
                // Dispatch events to mimic user input and trigger potential
                // listeners
                element.dispatchEvent(new Event('input', { bubbles: true,
                    cancelable: true }));
                element.dispatchEvent(new Event('change', { bubbles: true,
                    cancelable: true }));
                return { success: true, finalValue: element.value };
            } catch (error) {
                console.error(`[Evaluate] Error setting value for
                ${selector}:`, error);
                return { success: false, error: error.message,
                    finalValue: element.value };
            }
        }
    """

    try:
        element = page.locator(selector)
        # Increase timeout for visibility check
        element.wait_for(state="visible", timeout=5000)
        result = page.evaluate(script, [selector, datetime_str])

        if not result or not result.get("success"):
            error_msg = (
                result.get("error", "Unknown error")
                if result
                else "Script execution failed"
            )
            raise Exception(
                f"Failed to set datetime via page.evaluate for '{selector}'."
                f" Error: {error_msg}"
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
            f"Failed to set datetime element '{selector}' to '{datetime_str}'."
            f"Original error: {e}"
        ) from e


def speichern(page):
    submit_button = page.locator('button[type="submit"]:has-text("Speichern")')
    submit_button.scroll_into_view_if_needed()
    submit_button.click()


def set_meeting_title(meeting_title, page):
    m_name = 'input[name="name"]'
    # We've resorted to JavaScript for this seemingly trivial task.
    # Conventional approaches (element.fill) resulted in mysterious timeout
    # issues, hence this elaborate solution.
    page.evaluate(f"""
        const el = document.querySelector('{m_name}');
        if (el) {{
            el.value = '{meeting_title}';
            el.dispatchEvent(new Event('input', {{ bubbles: true }}));
            el.dispatchEvent(new Event('change', {{ bubbles: true }}));
        }} else {{
            console.error(`[Evaluate] Element not found: {m_name}`);
        }}
    """)


@pytest.mark.browser
def test_edit_meeting_browser(page: Page, live_server_url, session) -> None:
    """ Needs full browser test because listening for changes in attendees /
    guests for a meeting did require some javascript to dynamically updated the
    dropdowns of people.
    """

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

    # Create a working group
    page.goto(live_server_url + "/working_groups/add")
    page.wait_for_load_state("networkidle", timeout=10000)  # Wait for page load
    group_name_input = page.locator('textarea[name="name"]')
    group_name = f"Browser Test Group {datetime.now().isoformat()}"
    group_name_input.fill(group_name)
    user_select_input = page.locator('input[id="users-ts-control"]')
    user_select_input.wait_for(state='visible', timeout=3000)
    user_select_input.click()
    user_select_input.fill('Admin User')
    admin_option = page.locator(
        '.ts-dropdown-content .option:has-text("Admin User")'
    )
    admin_option.wait_for(state='visible', timeout=3000)
    admin_option.click()
    user_select_input.fill('Test User')  # Start typing again
    test_option = page.locator(
        '.ts-dropdown-content .option:has-text("Test User")'
    )
    test_option.wait_for(state="visible", timeout=3000)
    test_option.click()
    speichern(page)

    # We are now in working groups overview page.
    # Click on the created working group:
    page.locator('a:has-text("Browser Test Group")').click()
    # new meeting:
    page.locator('a:has-text("Sitzung hinzufügen")').click()
    meeting_title = "Initial Browser Meeting"

    set_meeting_title(meeting_title, page)
    meeting_time = utcnow() + timedelta(hours=1)
    set_datetime_element(page, 'input[name="time"]', meeting_time)

    speichern(page)

    page.wait_for_load_state("networkidle", timeout=10000)

    # Edit the meeting - Click Actions dropdown, then Edit link
    aktionen_button = page.locator('a.dropdown-toggle:has-text("Aktionen")')
    aktionen_button.click()
    bearbeiten_link = page.locator('.dropdown-menu a:has-text("Bearbeiten")')
    bearbeiten_link.wait_for(state="visible", timeout=5000)
    bearbeiten_link.click()
    page.wait_for_load_state("networkidle", timeout=10000)

    # Add External User to attendees
    attendees_input = page.locator('input[id="attendees-ts-control"]')
    attendees_input.wait_for(state='visible', timeout=3000)
    attendees_input.click()
    attendees_input.fill('External User')
    external_option = page.locator(
        '.ts-dropdown-content .option:has-text("External User")'
    )
    external_option.wait_for(state='visible', timeout=3000)
    external_option.click()

    speichern(page)
    page.wait_for_load_state("networkidle", timeout=10000)

    # Verify External User is now an attendee
    attendees_list = page.locator('ul.generic-user-list')
    expect(attendees_list).to_contain_text('External User')
    expect(attendees_list).to_contain_text('Admin User')  # Original user
    expect(attendees_list).to_contain_text('Test User')  # Original user

    # Remove Admin User
    aktionen_button = page.locator('a.dropdown-toggle:has-text("Aktionen")')
    aktionen_button.click()
    bearbeiten_link = page.locator('.dropdown-menu a:has-text("Bearbeiten")')
    bearbeiten_link.wait_for(state="visible", timeout=5000)
    bearbeiten_link.click()
    page.wait_for_load_state("networkidle", timeout=10000)

    # Find the row for Admin User using the disabled name input The value
    # attribute of the disabled input holds the full name
    admin_user_row_selector = (
        '.attendance-row:has(input[name$="-fullname"][value="Admin User"])'
    )
    admin_user_row = page.locator(admin_user_row_selector)
    admin_user_row.wait_for(state="visible", timeout=5000)

    # Find and click the 'Entfernen' checkbox within that row
    remove_checkbox_selector = 'input[name$="-remove"]'
    remove_checkbox = admin_user_row.locator(remove_checkbox_selector)
    remove_checkbox.wait_for(state="visible", timeout=3000)
    remove_checkbox.check()  # Use check() for checkboxes

    speichern(page)
    page.wait_for_load_state("networkidle", timeout=10000)

    # Verify Admin User is removed, others remain
    attendees_list = page.locator('ul.generic-user-list')
    expect(attendees_list).to_be_visible(timeout=5000)
    expect(attendees_list).not_to_contain_text("Admin User")
    expect(attendees_list).to_contain_text("External User")
    expect(attendees_list).to_contain_text("Test User")


@pytest.mark.browser
def test_edit_meeting_document(
    page: Page, live_server_url, session, pdf_vemz
) -> None:

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

    # Create a working group
    page.goto(live_server_url + "/working_groups/add")
    page.wait_for_load_state("networkidle", timeout=10000)  # Wait for page load
    group_name_input = page.locator('textarea[name="name"]')
    group_name = f"Browser Test Group {datetime.now().isoformat()}"
    group_name_input.fill(group_name)
    user_select_input = page.locator('input[id="users-ts-control"]')
    user_select_input.wait_for(state='visible', timeout=3000)
    user_select_input.click()
    user_select_input.fill('Admin User')
    admin_option = page.locator(
        '.ts-dropdown-content .option:has-text("Admin User")'
    )
    admin_option.wait_for(state='visible', timeout=3000)
    admin_option.click()
    user_select_input.fill('Test User')  # Start typing again
    test_option = page.locator(
        '.ts-dropdown-content .option:has-text("Test User")'
    )
    test_option.wait_for(state="visible", timeout=3000)
    test_option.click()
    speichern(page)

    # We are now in working groups overview page.
    # Click on the created working group:
    page.locator('a:has-text("Browser Test Group")').click()
    # new meeting:
    page.locator('a:has-text("Sitzung hinzufügen")').click()
    meeting_title = "Initial Browser Meeting"
    set_meeting_title(meeting_title, page)
    meeting_time = utcnow() + timedelta(hours=1)
    set_datetime_element(page, 'input[name="time"]', meeting_time)

    # Upload a document
    file_input = page.locator('input[type="file"][name="files"]')
    file_input.wait_for(state='visible', timeout=3000)
    filename, file_content = pdf_vemz
    file_input.set_input_files(files=[{
        'name': filename,
        'mimeType': 'application/pdf',
        'buffer': file_content
    }])

    speichern(page)
    page.wait_for_load_state('networkidle', timeout=10000)

    # Verify the document is listed
    meeting_documents = page.locator('.meeting-documents')
    expect(meeting_documents).to_be_visible(timeout=5000)
    expect(meeting_documents).to_contain_text(filename)


def test_copy_agenda_items_without_description(client):
    client.login_admin()
    users = [
        User(email="max@example.org", first_name="Max", last_name="Müller"),
        User(email="alexa@example.org", first_name="Alexa", last_name="A"),
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
    assert dest_updated.agenda_items[0].description == ''


def test_export_meeting_formats(client):
    client.login_admin()
    users = [
        User(email='max@example.org', first_name='Max', last_name='Müller'),
        User(email='alexa@example.org', first_name='Alexa', last_name='A'),
    ]
    for user in users:
        user.set_password('test')
        client.db.add(user)
    client.db.commit()

    working_group = WorkingGroup(name='Export Test Group', leader=users[0])
    working_group.users.extend(users)
    client.db.add(working_group)

    meeting_time = fix_utc_to_local_time(utcnow())

    meeting = Meeting(
        name='Meeting for Export',
        time=meeting_time,
        attendees=users,
        working_group=working_group,
    )
    client.db.add(meeting)
    client.db.commit()
    client.db.refresh(meeting)

    # Add an agenda item for content
    page = client.get(f'/meetings/{meeting.id}/add')
    page.form['title'] = 'Export Agenda Item'
    page.form['description'] = 'Details for export.'
    page.form.submit().follow()

    # Test PDF Export
    pdf_export_url = f'/meetings/{meeting.id}/export'
    pdf_response = client.get(pdf_export_url)
    assert pdf_response.status_code == 200
    assert pdf_response.content_type == 'application/pdf'
    assert pdf_response.content_length > 0
    assert b'%PDF' in pdf_response.body  # Basic check for PDF magic number

    # Test DOCX Export
    docx_export_url = f'/meetings/{meeting.id}/export/docx'
    docx_response = client.get(docx_export_url)
    assert docx_response.status_code == 200
    assert docx_response.content_type == (
        'application/vnd.openxmlformats-officedocument.wordprocessingml'
        '.document'
    )
    assert docx_response.content_length > 0
    # Basic check for DOCX (PK zip header)
    assert docx_response.body.startswith(b'PK\x03\x04')
