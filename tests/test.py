from app.services.piru_watcher import PiruWatcher

watcher = PiruWatcher(
    base_url="https://piru.cedi.com.ar",
    interval=5
)

watcher.run()
