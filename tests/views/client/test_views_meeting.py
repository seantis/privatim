import pytest
from playwright.sync_api import Page, expect
from datetime import datetime, timedelta
import re
import transaction
import uuid

from privatim.models import User, WorkingGroup, Meeting, MeetingUserAttendance
from privatim.models.association_tables import AttendanceStatus
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sedate import utcnow
from privatim.models.meeting import MeetingEditEvent
from privatim.utils import fix_utc_to_local_time
from tests.views.client.utils import (
    set_datetime_element,
    manage_document,
    FileAction,
    upload_new_documents
)


def speichern(page):
    submit_button = page.locator('button[type="submit"]:has-text("Speichern")')
    submit_button.scroll_into_view_if_needed()
    submit_button.click()


def set_meeting_title(meeting_title, page):
    # We've resorted to JavaScript for this seemingly trivial task.
    # Conventional approaches (element.fill) resulted in mysterious timeout
    # issues, hence this elaborate solution.

    # FIXME: It might be because the meeting name if you create a new one
    # defaults to the working group name. It's still unclear why but we 
    # can just overwrite it.
    selector = '#name' 
    script = """
        (args) => {
            const [selector, meeting_title] = args;
            const el = document.querySelector(selector);
            if (el) {
                el.value = meeting_title;
                el.dispatchEvent(new Event('input', { bubbles: true }));
                el.dispatchEvent(new Event('change', { bubbles: true }));
            } else {
                console.error('[Evaluate] Element not found');
            }

        }
        """
    page.evaluate(script, [selector, meeting_title])


@pytest.mark.browser
def test_edit_meeting_users(page: Page, live_server_url, session) -> None:
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
    meeting_link = page.url

    # Verify the document is listed
    meeting_documents = page.locator('.meeting-documents')
    expect(meeting_documents).to_be_visible(timeout=5000)
    expect(meeting_documents).to_contain_text(filename)

    page.goto(live_server_url + "/activities")

    # 1. First an activity item is created
    page.wait_for_load_state('networkidle', timeout=10000)
    timeline_content = page.locator('.timeline-content')
    expect(timeline_content).to_be_visible(timeout=5000)
    expect(timeline_content).to_contain_text('Sitzung geplant')

    # Edit the meeting - Click Actions dropdown, then Edit link
    page.goto(meeting_link)
    aktionen_button = page.locator('a.dropdown-toggle:has-text("Aktionen")')
    aktionen_button.click()
    bearbeiten_link = page.locator('.dropdown-menu a:has-text("Bearbeiten")')
    bearbeiten_link.wait_for(state="visible", timeout=5000)
    bearbeiten_link.click()
    page.wait_for_load_state("networkidle", timeout=10000)

    # Edit meeting document
    file_input = page.locator('input[type="file"][name="files"]')
    file_input.wait_for(state='visible', timeout=3000)
    filename, file_content = pdf_vemz
    file_input.set_input_files(files=[{
        'name': filename,
        'mimeType': 'application/pdf',
        'buffer': file_content
    }])
    speichern(page)

    events = session.scalars(select(MeetingEditEvent)).all()
    assert len(events) == 3
    assert events[0].event_type == 'creation'
    assert events[1].event_type == 'update'
    assert events[2].event_type == 'file_update'

    # 3. View activities, there should be two entries, one where the meeting
    # was created and one where we added a file to the meeting
    # Now _that_ should be registered as _distinct_ activity event.
    page.goto(live_server_url + "/activities")
    page.wait_for_load_state('networkidle', timeout=10000)
    timeline_items = page.locator('.timeline-content')
    expect(timeline_items).to_have_count(3, timeout=5000)
    document_activity = page.locator(
        '.timeline-content:has-text("Sitzungsdokument(e) aktualisiert")'
    )

    expect(document_activity).to_be_visible(timeout=5000)
    expect(document_activity).to_contain_text(filename)
    expect(document_activity).to_contain_text(meeting_title)


@pytest.mark.browser
def test_edit_meeting_multiple_documents(
    page: Page, live_server_url, session, pdf_vemz, docx, pdf_full_text
) -> None:
    """ Extensive test for the "Add", "replace" "delete, and
    'additional' functionality provided by UploadMultipleFilesWithORMSupport
    """

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
    filename_vemz, file_content = pdf_vemz
    file_input.set_input_files(files=[{
        'name': filename_vemz,
        'mimeType': 'application/pdf',
        'buffer': file_content
    }])

    speichern(page)
    page.wait_for_load_state('networkidle', timeout=10000)
    meeting_link = page.url

    # Verify the document is listed
    meeting_documents = page.locator('.meeting-documents')
    expect(meeting_documents).to_be_visible(timeout=5000)
    expect(meeting_documents).to_contain_text(filename_vemz)

    page.goto(live_server_url + "/activities")

    # 1. First an activity item is created
    page.wait_for_load_state('networkidle', timeout=10000)
    timeline_content = page.locator('.timeline-content')
    expect(timeline_content).to_be_visible(timeout=5000)
    expect(timeline_content).to_contain_text('Sitzung geplant')

    # 2. Edit files in meeting.
    page.goto(meeting_link)
    aktionen_button = page.locator('a.dropdown-toggle:has-text("Aktionen")')
    aktionen_button.click()
    bearbeiten_link = page.locator('.dropdown-menu a:has-text("Bearbeiten")')
    bearbeiten_link.wait_for(state="visible", timeout=5000)
    bearbeiten_link.click()
    page.wait_for_load_state("networkidle", timeout=10000)

    # Replace the first document and add a new one
    # sidequest
    manage_document(page, index=0, action=FileAction.REPLACE,
                    file_data=docx)

    replaced_file = docx
    additional_file = pdf_full_text 
    upload_new_documents(page, files=[additional_file])
    speichern(page)
    page.wait_for_load_state('networkidle', timeout=10000)

    # we should have now fulltext_search.pdf  new file
    # And test.docx (which replaced pdf_vemz)
    # Verify documents: original gone, replaced and additional are present
    meeting_documents = page.locator('.meeting-documents')
    expect(meeting_documents).to_be_visible(timeout=5000)
    expect(meeting_documents).not_to_contain_text(filename_vemz)
    expect(meeting_documents).to_contain_text(replaced_file[0])
    expect(meeting_documents).to_contain_text(additional_file[0])

    # --- 2. Delete one document ---
    aktionen_button = page.locator('a.dropdown-toggle:has-text("Aktionen")')
    aktionen_button.click()
    bearbeiten_link = page.locator('.dropdown-menu a:has-text("Bearbeiten")')
    bearbeiten_link.wait_for(state="visible", timeout=5000)
    bearbeiten_link.click()
    page.wait_for_load_state("networkidle", timeout=10000)

    # To make the test robust, find the file to delete by its name
    file_widgets = page.locator('.upload-widget.with-data').all()
    file_titles = [w.locator('p.file-title').inner_text() for w in file_widgets]
    idx_to_delete = next(
        i for i, title in enumerate(file_titles) if replaced_file[0] in title
    )
    manage_document(page, index=idx_to_delete, action=FileAction.DELETE)
    speichern(page)
    page.wait_for_load_state('networkidle', timeout=10000)

    # Verify one document was deleted, the other remains
    meeting_documents = page.locator('.meeting-documents')
    expect(meeting_documents).to_be_visible(timeout=5000)
    expect(meeting_documents).not_to_contain_text(replaced_file[0])
    expect(meeting_documents).to_contain_text(additional_file[0])

    # Delete all now
    page.goto(meeting_link)
    aktionen_button = page.locator('a.dropdown-toggle:has-text("Aktionen")')
    aktionen_button.click()
    bearbeiten_link = page.locator('.dropdown-menu a:has-text("Bearbeiten")')
    bearbeiten_link.wait_for(state="visible", timeout=5000)
    bearbeiten_link.click()
    page.wait_for_load_state("networkidle", timeout=10000)

    manage_document(page, index=0, action=FileAction.DELETE)
    upload_new_documents(page, files=[pdf_full_text, docx])
    # 2 new files

    speichern(page)
    page.wait_for_load_state('networkidle', timeout=10000)
    meeting_documents = page.locator('.meeting-documents')
    expect(meeting_documents).to_be_visible(timeout=5000)
    expect(meeting_documents).to_contain_text(pdf_full_text[0])
    expect(meeting_documents).to_contain_text(docx[0])

    page.goto(live_server_url + "/activities")

    # TODO: Check activity after all those edits
    page.wait_for_load_state('networkidle', timeout=10000)
    timeline_content = page.locator('.timeline-content')
    # 
    # first we have added one, then replaced the first one and added a new one
    # then we have deleted the docx
    # then we deleted the other one
    # and aded two completly new ones


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


@pytest.mark.browser
def test_remove_and_readd_working_group_member_in_meeting(
    page: Page, live_server_url, session
) -> None:
    """
    Tests that a working group member, initially an attendee,
    can be removed from a meeting and then re-added via the 'Guests'
    dropdown.
    """
    run_id = uuid.uuid4().hex[:8]  # Generate a unique ID for this test run

    admin_first_name = f'Admin{run_id}'
    admin_last_name = 'User'
    admin_full_name = f'{admin_first_name} {admin_last_name}'
    admin_email_value = f'admin_{run_id}@example.org'

    member_first_name = f'Member{run_id}'
    member_last_name = 'Person'
    member_full_name = f'{member_first_name} {member_last_name}'
    member_email_value = f'member_{run_id}@example.org'

    admin_user = User(
        email=admin_email_value,
        first_name=admin_first_name,
        last_name=admin_last_name,
    )
    admin_user.set_password("test")
    member_user = User(
        email=member_email_value,
        first_name=member_first_name,
        last_name=member_last_name,
    )
    member_user.set_password("test")
    session.add_all([admin_user, member_user])
    transaction.commit()

    # Login as admin
    page.goto(live_server_url + "/login")
    page.locator('input[name="email"]').fill(admin_email_value)
    page.locator('input[name="password"]').fill("test")
    page.locator('button[type="submit"]').click()
    page.wait_for_load_state("networkidle", timeout=10000)
    expect(page).not_to_have_url(re.compile(r".*/login$"), timeout=5000)

    # Create a working group with Admin and Member User
    page.goto(live_server_url + "/working_groups/add")
    page.wait_for_load_state("networkidle", timeout=10000)
    group_name = f"Re-add Test Group {datetime.now().isoformat()}"
    page.locator('textarea[name="name"]').fill(group_name)

    user_select_input = page.locator('input[id="users-ts-control"]')
    user_select_input.wait_for(state='visible', timeout=3000)
    user_select_input.click()
    user_select_input.fill(admin_full_name)
    page.locator(
        f'.ts-dropdown-content .option:has-text("{admin_full_name}")'
    ).click()

    # Click outside to close dropdown if necessary, then fill for next user
    page.locator('textarea[name="name"]').click() # Click somewhere else
    user_select_input.click()
    user_select_input.fill(member_full_name)
    page.locator(
        f'.ts-dropdown-content .option:has-text("{member_full_name}")'
    ).click()
    speichern(page)
    page.wait_for_load_state("networkidle", timeout=10000)

    # Go to the created working group and add a meeting
    page.locator(f'a:has-text("{group_name}")').click()
    page.locator('a:has-text("Sitzung hinzufügen")').click()
    meeting_title = "Meeting for Re-add Test"
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

    # Remove "Member Person"
    member_user_row_selector = (
        f'.attendance-row:has(input[name$="-fullname"]'
        f'[value="{member_full_name}"])'
    )
    member_user_row = page.locator(member_user_row_selector)
    member_user_row.wait_for(state="visible", timeout=5000)
    remove_checkbox = member_user_row.locator('input[name$="-remove"]')
    remove_checkbox.check()
    speichern(page)
    page.wait_for_load_state("networkidle", timeout=10000)

    # Verify "Member Person" is removed, "Admin User" remains
    attendees_list_view = page.locator('ul.generic-user-list')
    expect(attendees_list_view).to_be_visible(timeout=5000)
    expect(attendees_list_view).not_to_contain_text(member_full_name)
    expect(attendees_list_view).to_contain_text(admin_full_name)

    # Edit the meeting again
    aktionen_button = page.locator('a.dropdown-toggle:has-text("Aktionen")')
    aktionen_button.click()
    bearbeiten_link = page.locator('.dropdown-menu a:has-text("Bearbeiten")')
    bearbeiten_link.wait_for(state="visible", timeout=5000)
    bearbeiten_link.click()
    page.wait_for_load_state("networkidle", timeout=10000)

    # Try to re-add "Member Person" via the "Guests" (attendees) dropdown
    guests_input = page.locator('input[id="attendees-ts-control"]')
    guests_input.wait_for(state='visible', timeout=3000)
    guests_input.click()
    guests_input.fill(member_full_name)
    member_option_in_dropdown = page.locator(
        f'.ts-dropdown-content .option:has-text("{member_full_name}")'
    )
    # This is the crucial check: the removed member should be available
    expect(member_option_in_dropdown).to_be_visible(timeout=3000)
    member_option_in_dropdown.click()
    speichern(page)
    page.wait_for_load_state("networkidle", timeout=10000)

    # Verify "Member Person" is re-added and "Admin User" is still there
    attendees_list_view = page.locator('ul.generic-user-list')
    expect(attendees_list_view).to_be_visible(timeout=5000)
    expect(attendees_list_view).to_contain_text(member_full_name)
    expect(attendees_list_view).to_contain_text(admin_full_name)
