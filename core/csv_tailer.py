import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class CSVChangeHandler(FileSystemEventHandler):
    def __init__(self, on_update_callback):
        self.on_update_callback = on_update_callback

    def on_modified(self, event):
        if event.src_path.endswith(".csv"):
            self.on_update_callback()

class CSVTailer:
    def __init__(self, file_path, on_update_callback):
        self.file_path = file_path
        self.on_update_callback = on_update_callback
        self.last_position = 0
        self.handler = CSVChangeHandler(self.read_new_lines)
        self.observer = Observer()
        self.observer.schedule(self.handler, path=file_path.rsplit('/', 1)[0], recursive=False)

    def start(self):
        self.observer.start()

    def stop(self):
        self.observer.stop()
        self.observer.join()

    def read_new_lines(self):
        try:
            with open(self.file_path, "r") as f:
                f.seek(self.last_position)
                lines = f.readlines()
                self.last_position = f.tell()
                if lines:
                    self.on_update_callback(lines)
        except Exception as e:
            print(f"[ERROR] Reading CSV: {e}")
