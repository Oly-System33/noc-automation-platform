from playwright.sync_api import sync_playwright

PIRU_URL = "https://piru.cedi.com.ar"
STORAGE_PATH = "piru_storage.json"


def main():

    print("\n[PIRU] Login inicial requerido.\n")

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=False,
            args=["--no-sandbox"]
        )

        context = browser.new_context()

        page = context.new_page()

        page.goto(PIRU_URL)

        input(
            "\nLogueate con Microsoft SSO y cuando estés dentro del dashboard PIRU presioná ENTER...\n"
        )

        context.storage_state(path=STORAGE_PATH)

        print(
            f"\n[PIRU] storage_state guardado correctamente en {STORAGE_PATH}\n"
        )

        browser.close()


if __name__ == "__main__":
    main()
