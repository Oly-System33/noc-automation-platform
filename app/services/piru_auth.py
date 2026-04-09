from playwright.sync_api import sync_playwright


def get_token_from_session():

    with sync_playwright() as p:

        browser = p.chromium.launch(headless=True)

        context = browser.new_context(
            storage_state="piru_storage.json"
        )

        page = context.new_page()

        page.goto("https://piru.cedi.com.ar")

        storage = page.evaluate("localStorage")

        token = storage.get("token")

        browser.close()

        return token
