import threading
import time

try:
    import winsound
except ImportError:
    winsound = None


class AlertManager:
    def __init__(self):
        self.level = 0
        self._run = True
        self._last = {1: 0.0, 2: 0.0, 3: 0.0}
        threading.Thread(target=self._loop, daemon=True).start()

    def _beep(self, f, ms):
        if winsound:
            winsound.Beep(f, ms)
        else:
            print("\a", end="", flush=True)

    def cue(self, f=1000, ms=300):
        threading.Thread(target=self._beep, args=(f, ms), daemon=True).start()

    def set_level(self, level):
        self.level = level

    def _loop(self):
        while self._run:
            lvl, now = self.level, time.monotonic()
            if lvl == 3:
                for _ in range(3):
                    if self.level != 3:
                        break
                    self._beep(3120, 170)
                    time.sleep(0.15)
                time.sleep(0.27)
            elif lvl == 2 and now - self._last[2] >= 6.0:
                self._last[2] = now
                self._beep(1300, 200)
                self._beep(1300, 200)
            elif lvl == 1 and now - self._last[1] >= 20.0:
                self._last[1] = now
                self._beep(800, 200)
            else:
                time.sleep(0.05)

    def stop(self):
        self._run = False