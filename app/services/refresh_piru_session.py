from playwright.sync_api import sync_playwright


PIRU_URL = "https://piru.cedi.com.ar"


def refresh_piru_session(storage_path="piru_storage.json"):

    print("\n[PIRU] Sesión expirada. Iniciando re-login automático...\n")

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=False,
            args=["--no-sandbox"]
        )

        context = browser.new_context()

        page = context.new_page()

        page.goto(PIRU_URL)

        input(
            "\nCompletá login Microsoft SSO y presioná ENTER cuando estés dentro de PIRU...\n"
        )

        context.storage_state(path=storage_path)

        browser.close()

    print("\n[PIRU] Nueva sesión guardada correctamente.\n")
