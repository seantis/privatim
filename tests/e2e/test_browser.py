# """
# End-to-end tests that imports and exports product catalogues.
# """
# from pathlib import Path
# from typing import Any
#
# import pytest
# from playwright.sync_api import BrowserContext
# from playwright.sync_api import Page
# from playwright.sync_api import StorageState
# from playwright.sync_api import expect
#
# pytestmark = pytest.mark.e2e
#
#
# @pytest.fixture()
# def browser_context_args(
#     browser_context_args: dict[str, Any],
#     authenticated: StorageState
# ):
#     return {
#         **browser_context_args,
#         'storage_state': authenticated
#     }
#
#
#
# def test_imports_catalogue_with_assets(static_server, context: BrowserContext):
#     page: Page = context.new_page()
#     page.goto('http://localhost:7654/activities')
#
