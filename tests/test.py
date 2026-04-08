from app.services.piru_watcher import PiruWatcher
import os
from dotenv import load_dotenv

load_dotenv(".env")


PIRU_TOKEN = os.getenv("PIRU_TOKEN")


watcher = PiruWatcher(
    base_url="https://piru.cedi.com.ar",
    token=PIRU_TOKEN,
    interval=5
)

watcher.run()
