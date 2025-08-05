import re
import mimetypes
from zoneinfo import ZoneInfo
from playwright.sync_api import expect
from enum import Enum
from playwright.sync_api import Page


def set_datetime_element(page, selector, dt):
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


class FileAction(Enum):
    KEEP = 'keep'
    DELETE = 'delete'
    REPLACE = 'replace'


def manage_document(
    page: Page,
    index: int,
    action: FileAction,
    file_data: tuple[str, bytes] | None = None
):
    """Manages an existing document. Frontend for
    `UploadMultipleFilesWithOrmSupport`."""
    radio_selector = f'input[name="files-{index}"][value="{action.value}"]'
    radio_button = page.locator(radio_selector)
    expect(radio_button).to_have_count(1)
    radio_button.click()

    if action == FileAction.REPLACE:
        if not file_data:
            raise ValueError('file_data must be provided for REPLACE action')

        filename, content = file_data
        mime_type, _ = mimetypes.guess_type(filename)
        file_input = page.locator(f'input[id="files-{index}"][type="file"]')
        file_input.set_input_files(
            files={
                'name': filename,
                'mimeType': mime_type or 'application/octet-stream',
                'buffer': content
            }
        )


def upload_new_documents(page: Page, files: list[tuple[str, bytes]]):
    """Uploads one or more new documents."""
    if not files:
        return

    file_input = page.locator('input[id="files"][multiple][type="file"]')
    file_payloads = []
    for name, content in files:
        mime_type, _ = mimetypes.guess_type(name)
        file_payloads.append({
            'name': name,
            'mimeType': mime_type or 'application/octet-stream',
            'buffer': content
        })
    file_input.set_input_files(file_payloads)
