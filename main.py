if __name__ == "__main__":
    # First of all: errors from here on (even a missing PySide6) go to error.log and a message box
    import error_log
    error_log.install("Lorebook Studio")

from app.main_window import run

if __name__ == "__main__":
    run()
