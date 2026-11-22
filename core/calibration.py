import json
from dataclasses import dataclass, asdict
from pathlib import Path
import numpy as np

CAL_PATH = Path("config/calibration.json")


@dataclass
class Calibration:
    ear_open: float
    ear_closed: float
    ear_thr: float
    mar_base: float
    pitch_base: float


def save(cal: Calibration):
    CAL_PATH.write_text(json.dumps(asdict(cal), indent=2))


def load():
    try:
        return Calibration(**json.loads(CAL_PATH.read_text()))
    except Exception:
        return None


class Calibrator:
    OPEN_S, CLOSED_S, SKIP_S = 8.0, 4.0, 1.5

    def __init__(self, ratio):
        self.ratio = ratio
        self.reset()

    def reset(self):
        self.phase = "WAIT"
        self.t0 = None
        self.open, self.closed, self.mar, self.pitch = [], [], [], []
        self.cue = False
        self.msg = "Sit normally, look at the road. Press SPACE to calibrate"

    def start(self, t):
        self.reset()
        self.phase, self.t0 = "OPEN", t

    def update(self, m, t):
        """Returns Calibration when finished, else None. Status text in self.msg."""
        if self.phase == "WAIT":
            return None
        el = t - self.t0
        if self.phase == "OPEN":
            if m.face:
                self.open.append(m.ear)
                self.mar.append(m.mar)
                self.pitch.append(m.pitch)
            self.msg = f"LOOK STRAIGHT, BLINK NORMALLY  {max(0, self.OPEN_S - el):.0f}s"
            if el >= self.OPEN_S:
                self.phase, self.t0, self.cue = "CLOSED", t, True
            return None
        if self.phase == "CLOSED":
            if m.face and el > self.SKIP_S:
                self.closed.append(m.ear)
            self.msg = "CLOSE YOUR EYES UNTIL THE BEEP"
            if el >= self.CLOSED_S:
                return self._finish()
        return None

    def _finish(self):
        self.cue = True
        if len(self.open) < 30 or len(self.closed) < 15:
            self.reset()
            self.msg = "FAILED: face not tracked. Press SPACE to retry"
            return None
        eo = float(np.percentile(self.open, 90))
        ec = float(np.median(self.closed))
        if eo - ec < 0.06:
            self.reset()
            self.msg = "FAILED: eyes not closed enough. Press SPACE to retry"
            return None
        cal = Calibration(eo, ec, ec + self.ratio * (eo - ec),
                          float(np.median(self.mar)), float(np.median(self.pitch)))
        self.reset()
        return cal