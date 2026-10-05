#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Scrolling progress bar animation
- RollingBar: scrolls back and forth  [====>========]  →  [====<========]
- Spinner:    rotating icon   ⠋ ⠙ ⠹ ⠸ ...
- Automatically cleans up the current line without polluting log output
"""
import sys
import threading
import time


class RollingBar:
    """
    Arrow progress bar that scrolls back and forth
        [===========>========]        # rightward
        [========<============]        # leftward
    """

    def __init__(self, width=24, prefix="", suffix="", interval=0.08):
        self.width = max(4, width)
        self.prefix = prefix
        self.suffix = suffix
        self.interval = interval

        self.pos = 0
        self.direction = 1  # 1=rightward, -1=leftward
        self._running = False
        self._thread = None
        self._last_len = 0
        self._lock = threading.RLock()

    def _render(self):
        buf = ["="] * self.width
        if self.direction == 1:
            buf[self.pos] = ">"
        else:
            buf[self.pos] = "<"
        bar = "[" + "".join(buf) + "]"
        return f"{self.prefix}{bar}{self.suffix}"

    def _loop(self):
        while self._running:
            line = self._render()
            with self._lock:
                sys.stdout.write("\r" + " " * self._last_len + "\r" + line)
                sys.stdout.flush()
                self._last_len = len(line)

            self.pos += self.direction
            if self.pos >= self.width - 1:
                self.pos = self.width - 1
                self.direction = -1
            elif self.pos <= 0:
                self.pos = 0
                self.direction = 1

            time.sleep(self.interval)

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        return self

    def stop(self, final_msg=""):
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)
        with self._lock:
            sys.stdout.write("\r" + " " * self._last_len + "\r")
            if final_msg:
                sys.stdout.write(final_msg + "\n")
            sys.stdout.flush()
        self._last_len = 0

    def update_suffix(self, text):
        self.suffix = text

    def __enter__(self):
        return self.start()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


class Spinner:
    """Rotating spinner, suited to operations whose progress cannot be estimated"""

    FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    FRAMES_ASCII = ["|", "/", "-", "\\"]

    def __init__(self, prefix="", interval=0.08, ascii_only=False):
        self.prefix = prefix
        self.interval = interval
        self.frames = self.FRAMES_ASCII if ascii_only else self.FRAMES
        self._running = False
        self._thread = None
        self._idx = 0
        self._last_len = 0
        self._lock = threading.RLock()

    def _loop(self):
        while self._running:
            frame = self.frames[self._idx % len(self.frames)]
            line = f"{self.prefix} {frame}"
            with self._lock:
                sys.stdout.write("\r" + " " * self._last_len + "\r" + line)
                sys.stdout.flush()
                self._last_len = len(line)
            self._idx += 1
            time.sleep(self.interval)

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        return self

    def stop(self, final_msg=""):
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)
        with self._lock:
            sys.stdout.write("\r" + " " * self._last_len + "\r")
            if final_msg:
                sys.stdout.write(final_msg + "\n")
            sys.stdout.flush()
        self._last_len = 0

    def __enter__(self):
        return self.start()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()