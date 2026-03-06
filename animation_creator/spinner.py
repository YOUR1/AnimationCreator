"""Simple spinner for showing progress during long operations."""

import sys
import threading
import time


class Spinner:
    """A simple CLI spinner to indicate ongoing work."""

    FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    def __init__(self, message: str = ""):
        """Initialize spinner with optional message."""
        self.message = message
        self._stop_event = threading.Event()
        self._thread = None
        self._start_time = None

    def _format_elapsed(self, seconds: float) -> str:
        """Format elapsed time as mm:ss or just seconds."""
        if seconds < 60:
            return f"{int(seconds)}s"
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs:02d}s"

    def _spin(self):
        """Spin animation loop."""
        idx = 0
        while not self._stop_event.is_set():
            frame = self.FRAMES[idx % len(self.FRAMES)]
            elapsed = time.time() - self._start_time
            elapsed_str = self._format_elapsed(elapsed)
            line = f"\r  {frame} {self.message} [{elapsed_str}]"
            sys.stdout.write(line + " " * 10)  # Pad to clear previous longer text
            sys.stdout.flush()
            idx += 1
            time.sleep(0.1)

    def start(self, message: str = None):
        """Start the spinner."""
        if message:
            self.message = message
        self._stop_event.clear()
        self._start_time = time.time()
        self._thread = threading.Thread(target=self._spin)
        self._thread.start()

    def stop(self, final_message: str = None):
        """Stop the spinner."""
        elapsed = time.time() - self._start_time if self._start_time else 0
        self._stop_event.set()
        if self._thread:
            self._thread.join()
        # Clear the spinner line
        sys.stdout.write("\r" + " " * 80 + "\r")
        if final_message:
            elapsed_str = self._format_elapsed(elapsed)
            print(f"  ✓ {final_message} [{elapsed_str}]")
        sys.stdout.flush()

    def update(self, message: str):
        """Update the spinner message."""
        self.message = message

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, *args):
        """Context manager exit."""
        self.stop()
