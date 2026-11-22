import threading
import time
from collections import deque
from dataclasses import asdict
import cv2
from config.settings import Settings
from core.capture import Camera
from core.landmarks import FaceTracker
from core.metrics import compute, FrameMetrics, LEFT_EYE, RIGHT_EYE
from core import calibration as calmod
from engine.fatigue_score import FatigueEngine, FatigueState, LEVEL_NAMES
from engine.alert_manager import AlertManager

MOUTH = [78, 308, 13, 14]


def _nz(pts, idx, w, h):
    return [[round(float(pts[i][0] / w), 4), round(float(pts[i][1] / h), 4)] for i in idx]


class Pipeline(threading.Thread):
    def __init__(self, cam_index=0):
        super().__init__(daemon=True)
        self.cfg = Settings()
        self.cam_index = cam_index
        self.alerts = AlertManager()
        self.calib = calmod.Calibrator(self.cfg.ear_close_ratio)
        self.cal = calmod.load()
        self.engine = FatigueEngine(self.cal, self.cfg) if self.cal else None
        self.events = deque(maxlen=40)
        self.counts = {1: 0, 2: 0, 3: 0}
        self.peak = 0.0
        self.t_start = time.monotonic()
        self._lock = threading.Lock()
        self._jpeg, self._fid = None, 0
        self._cmd = False
        self._run = True
        self._state = {}
        self._publish(FrameMetrics(), FatigueState(), 0.0, None)

    # ---- public API ----
    def get_frame(self):
        with self._lock:
            return self._jpeg, self._fid

    def get_state(self):
        with self._lock:
            return self._state

    def request_calibration(self):
        self._cmd = True

    def stop(self):
        self._run = False
        self.alerts.stop()

    # ---- internals ----
    def _log(self, level, text):
        self.events.append({"t": time.strftime("%H:%M:%S"), "level": level, "text": text})

    def _publish(self, m, st, fps, lm, error=None):
        now = time.monotonic()
        if error:
            mode = "ERROR"
        elif self.engine is not None:
            mode = "MONITORING"
        elif self.calib.phase == "WAIT":
            mode = "WAITING"
        else:
            mode = "CALIBRATING"
        prog = 0.0
        if self.calib.phase == "OPEN":
            prog = (now - self.calib.t0) / self.calib.OPEN_S
        elif self.calib.phase == "CLOSED":
            prog = (now - self.calib.t0) / self.calib.CLOSED_S
        state = {
            "mode": mode, "error": error, "fps": round(fps), "face": m.face,
            "ear": round(m.ear, 3), "mar": round(m.mar, 3),
            "pitch": round(m.pitch, 1), "yaw": round(m.yaw, 1), "roll": round(m.roll, 1),
            "cal": asdict(self.cal) if self.cal else None,
            "cal_msg": self.calib.msg, "cal_phase": self.calib.phase,
            "cal_progress": min(1.0, max(0.0, prog)),
            "thr": {"yawn_mar": self.cfg.yawn_mar, "nod_deg": self.cfg.nod_deg},
            "score": round(st.score, 1), "level": st.level,
            "level_name": LEVEL_NAMES[st.level], "reason": st.reason,
            "closure_s": round(st.closure_s, 1), "head_down_s": round(st.head_down_s, 1),
            "perclos": round(st.perclos * 100), "long_blinks": st.long_blinks,
            "yawns": st.yawns, "nods": st.nods,
            "session": {"elapsed": int(now - self.t_start), "peak": round(self.peak),
                        "alerts": self.counts},
            "events": list(self.events), "lm": lm,
        }
        with self._lock:
            self._state = state

    def run(self):
        try:
            cam = Camera(self.cam_index).start()
            tracker = FaceTracker()
        except Exception as e:
            self._publish(FrameMetrics(), FatigueState(), 0.0, None, error=str(e))
            return
        last_id, fps, t0 = 0, 0.0, time.perf_counter()
        prev_lvl, prev_n = 0, (0, 0, 0)

        while self._run:
            if self._cmd:
                self._cmd = False
                self.engine, self.cal, prev_lvl = None, None, 0
                self.alerts.set_level(0)
                self.calib.start(time.monotonic())
                self._log(0, "CALIBRATION STARTED")

            fid, frame = cam.read()
            if frame is None or fid == last_id:
                time.sleep(0.004)
                continue
            last_id = fid
            t = time.monotonic()
            pts, mat = tracker.process(frame)
            m = compute(pts, mat)

            now = time.perf_counter()
            fps = 0.9 * fps + 0.1 / max(now - t0, 1e-6)
            t0 = now

            st = FatigueState()
            if self.engine is None:
                before = self.calib.phase
                done = self.calib.update(m, t)
                if self.calib.cue:
                    self.calib.cue = False
                    self.alerts.cue(1500, 300)
                if before == "CLOSED" and self.calib.phase != "CLOSED":
                    self.alerts.cue(1000, 400)
                if done:
                    calmod.save(done)
                    self.cal = done
                    self.engine = FatigueEngine(done, self.cfg)
                    prev_n = (0, 0, 0)
                    self._log(0, "CALIBRATION COMPLETE")
            else:
                st = self.engine.update(m, t)
                self.alerts.set_level(st.level)
                if st.level > prev_lvl:
                    self.counts[st.level] += 1
                    self._log(st.level, f"{LEVEL_NAMES[st.level]} // {st.reason}")
                elif st.level < prev_lvl:
                    self._log(0, f"RECOVERY // {LEVEL_NAMES[st.level]}")
                prev_lvl = st.level                
                n = (st.long_blinks, st.yawns, st.nods)
                for i, name in enumerate(("LONG BLINK", "YAWN", "HEAD NOD")):
                    if n[i] > prev_n[i]:
                        self._log(0, name + " DETECTED")
                prev_n = n
                self.peak = max(self.peak, st.score)

            lm = None
            if m.face:
                h, w = frame.shape[:2]
                x0, y0 = pts.min(axis=0)
                x1, y1 = pts.max(axis=0)
                lm = {"le": _nz(pts, LEFT_EYE, w, h), "re": _nz(pts, RIGHT_EYE, w, h),
                      "mo": _nz(pts, MOUTH, w, h),
                      "box": [round(float(x0 / w), 4), round(float(y0 / h), 4),
                              round(float(x1 / w), 4), round(float(y1 / h), 4)]}

            ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if ok:
                with self._lock:
                    self._jpeg, self._fid = buf.tobytes(), fid
            self._publish(m, st, fps, lm)

        cam.stop()