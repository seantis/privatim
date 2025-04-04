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
    local_tz = ZoneInfo('Europe/Zurich')
    local_dt = dt.astimezone(local_tz)
    datetime_str = local_dt.strftime('%Y-%m-%dT%H:%M')

    print(f"Attempting to set datetime for selector '{selector}' using page.evaluate with value '{datetime_str}'")

    # Define the JavaScript function to be executed in the browser context
    # This mirrors the logic from scratch_datetime_setter.js that worked manually
    script = """
        async (args) => {
            const [selector, dateTimeString] = args;
            console.log(`[Evaluate] Attempting: selector="${selector}", value="${dateTimeString}"`);
            const element = document.querySelector(selector);

            if (!element) {
                console.error('[Evaluate] Element not found.');
                return { success: false, error: 'Element not found', finalValue: null };
            }
            console.log('[Evaluate] Element found:', element);

            // Check visibility again inside evaluate (though Playwright waits should handle this)
            if (element.offsetParent === null) {
                 console.warn('[Evaluate] Element might not be visible (offsetParent is null).');
            }
            // Using checkVisibility() might be more reliable if available
            if (typeof element.checkVisibility === 'function' && !element.checkVisibility()) {
                 console.warn('[Evaluate] Element might not be visible (checkVisibility() is false).');
            }


            try {
                console.log('[Evaluate] Forcing focus on element...');
                element.focus();
                // Add a tiny delay after focus inside JS
                await new Promise(resolve => setTimeout(resolve, 50));

                console.log('[Evaluate] Setting element.value...');
                element.value = dateTimeString;
                const valueAfterSet = element.value;
                console.log(`[Evaluate] Value after setting: "${valueAfterSet}"`);

                // Check if the value actually stuck
                if (valueAfterSet !== dateTimeString) {
                    console.warn(`[Evaluate] Value did not stick! Expected "${dateTimeString}", got "${valueAfterSet}".`);
                    // Attempt to set again? Or just report failure.
                }

                // Add a tiny delay before dispatching events
                await new Promise(resolve => setTimeout(resolve, 50));

                console.log('[Evaluate] Dispatching input event...');
                element.dispatchEvent(new Event('input', { bubbles: true, cancelable: true }));

                console.log('[Evaluate] Dispatching change event...');
                element.dispatchEvent(new Event('change', { bubbles: true, cancelable: true }));

                // Optional: Dispatch blur event
                // console.log('[Evaluate] Dispatching blur event...');
                // element.dispatchEvent(new Event('blur', { bubbles: true, cancelable: true }));

                console.log('[Evaluate] Script execution finished successfully.');
                // Return success and the final value read from the element
                return { success: true, finalValue: element.value };

            } catch (error) {
                console.error('[Evaluate] Error during execution:', error);
                // Try to return the value even if error occurred during dispatch
                const finalValueOnError = element ? element.value : 'N/A';
                return { success: false, error: error.message, finalValue: finalValueOnError };
            }
        }
    """

    try:
        breakpoint()
        # Locate the element
        element = page.locator(selector)

        # Add robust waits before interaction
        print(f"Waiting for element '{selector}' to be visible and enabled...")

        # Scroll into view just in case
        print(f"Scrolling element '{selector}' into view...")
        element.scroll_into_view_if_needed()

        # Force focus using Playwright before evaluate
        print(f"Focusing element '{selector}' using Playwright...")
        element.focus(timeout=5000)

        # Add a small pause after focusing in Python
        page.wait_for_timeout(150) # Slightly longer pause

        print(f"Executing page.evaluate for '{selector}' with value '{datetime_str}'...")
        # Execute the async script
        result = page.evaluate(script, [selector, datetime_str])

        print(f"page.evaluate result: {result}")

        # Add a pause after evaluate to allow any async JS handlers on the page to run
        page.wait_for_timeout(300) # Longer pause after evaluate

        # Verify the result from the script and check the value again from Playwright
        final_value_script = result.get('finalValue') if result else 'N/A' # Handle case where result is None
        final_value_playwright = element.input_value() # Read value again via Playwright

        print(f"Value reported by script: '{final_value_script}'")
        print(f"Value read by Playwright after evaluate: '{final_value_playwright}'")

        if not result or not result.get('success'):
            error_msg = result.get('error', 'Unknown error or script did not return object') if result else 'Script execution failed entirely'
            print(f"Error: page.evaluate failed for '{selector}'. Error: {error_msg}. Script value: '{final_value_script}', Playwright value: '{final_value_playwright}'")
            raise Exception(f"Failed to set datetime element '{selector}' using page.evaluate. Error: {error_msg}")
        elif final_value_playwright != datetime_str:
             print(f"Warning: page.evaluate succeeded but final value mismatch for '{selector}'. Expected '{datetime_str}', Script reported: '{final_value_script}', Playwright read: '{final_value_playwright}'")
             # Decide if this is a failure condition - uncomment to fail the test
             # raise Exception(f"Failed to set datetime element '{selector}': value mismatch after page.evaluate.")
        else:
            print(f"Successfully set datetime for selector '{selector}' using page.evaluate. Final value: '{final_value_playwright}'")

    except Exception as e:
        print(f"Error setting datetime for selector '{selector}' using page.evaluate approach: {e}")
        # Add screenshot on failure
        # Ensure selector is filename-safe
        safe_selector = re.sub(r'[^a-zA-Z0-9_-]', '_', selector)
        screenshot_path = f"playwright-fail-{safe_selector}.png"
        try:
            page.screenshot(path=screenshot_path, full_page=True)
            print(f"Screenshot saved to {screenshot_path}")
        except Exception as se:
            print(f"Failed to save screenshot: {se}")
        # Re-raise the original exception
        raise Exception(f"Failed to set datetime element with selector '{selector}' using page.evaluate.") from e


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
    breakpoint() # this is the last breakpoint

    # wer are now in working groups overview page.
    # click on the created working group:
    page.locator('a:has-text("Browser Test Group")').click()
    # new meeting:
    page.locator('a:has-text("Sitzung hinzufügen")').click()
    meeting_name = f"Initial Browser Meeting {datetime.now().isoformat()}"
    name_selector = 'input[name="name"]'

    # Use page.evaluate to set the value directly via JavaScript
    print(f"Attempting to set value for '{name_selector}' using page.evaluate...")
    page.evaluate(f"""
        const el = document.querySelector('{name_selector}');
        if (el) {{
            el.value = '{meeting_name}';
            el.dispatchEvent(new Event('input', {{ bubbles: true }})); // Trigger input event
            el.dispatchEvent(new Event('change', {{ bubbles: true }})); // Trigger change event
            console.log(`[Evaluate] Set value for {name_selector} to: ${el.value}`);  # noqa: F821
        }} else {{
            console.error(`[Evaluate] Element not found: {name_selector}`);
        }}
    """)
    print(f"Finished page.evaluate for '{name_selector}'.")

    # Explicitly wait for the page to settle *after* the evaluate call
    print("Waiting for network idle after setting name via evaluate...")
    page.wait_for_load_state("networkidle", timeout=15000) # Increased timeout slightly
    print("Network idle confirmed.")

    # Set the meeting time using the helper function
    meeting_time = utcnow() + timedelta(hours=2) # Set time 2 hours from now
    print("About to set datetime element...")
    # breakpoint() # Keep breakpoint here or move after set_datetime_element if needed

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
