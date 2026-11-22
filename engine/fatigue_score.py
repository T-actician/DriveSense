import math
from collections import deque
from dataclasses import dataclass

LEVEL_NAMES = ["NORMAL", "CAUTION", "WARNING", "CRITICAL"]


@dataclass
class FatigueState:
    score: float = 0.0
    level: int = 0
    closure_s: float = 0.0
    head_down_s: float = 0.0
    perclos: float = 0.0
    long_blinks: int = 0
    yawns: int = 0
    nods: int = 0
    face_lost: bool = False
    reason: str = ""


def _clamp(x):
    return max(0.0, min(1.0, x))


class FatigueEngine:
    def __init__(self, cal, cfg):
        self.cal, self.cfg = cal, cfg
        self.samples = deque()  # (t, dt, closed)
        self.long_blinks, self.yawns, self.nods = deque(), deque(), deque()
        self.score, self.level, self.last_t = 0.0, 0, None
        self.lost_since = None
        self.below_since = None
        self.last_event_t = None
        self._reset_ongoing()

    def _reset_ongoing(self):
        self.closed_since = self.yawn_since = self.down_since = None
        self.yawn_active = self.nod_active = False

    def update(self, m, t):
        cfg, c = self.cfg, self.cal
        if self.last_event_t is None:
            self.last_event_t = t
        dt = 0.0 if self.last_t is None else min(t - self.last_t, 0.5)
        self.last_t = t
        st = FatigueState()
        closure = down_s = 0.0

        if not m.face:
            if self.lost_since is None:
                self.lost_since = t
            st.face_lost = (t - self.lost_since) >= cfg.face_lost_s
            if st.face_lost:
                self.last_event_t = t
            self._reset_ongoing()
        else:
            self.lost_since = None
            head_down = (m.pitch - c.pitch_base) > cfg.nod_deg
            eyes_closed = m.ear < c.ear_thr and not head_down
            self.samples.append((t, dt, eyes_closed))

            if eyes_closed:
                if self.closed_since is None:
                    self.closed_since = t
                closure = t - self.closed_since
                if closure >= cfg.recover_closure_s:
                    self.last_event_t = t
            else:
                if self.closed_since is not None and (t - self.closed_since) >= cfg.long_blink_s:
                    self.long_blinks.append(t)
                    self.last_event_t = t
                self.closed_since = None

            if m.mar > cfg.yawn_mar:
                if self.yawn_since is None:
                    self.yawn_since = t
                if not self.yawn_active and (t - self.yawn_since) >= cfg.yawn_s:
                    self.yawn_active = True
                    self.yawns.append(t)
                    self.last_event_t = t
            else:
                self.yawn_since, self.yawn_active = None, False

            if head_down:
                self.last_event_t = t
                if self.down_since is None:
                    self.down_since = t
                down_s = t - self.down_since
                if not self.nod_active and down_s >= cfg.nod_s:
                    self.nod_active = True
                    self.nods.append(t)
            else:
                self.down_since, self.nod_active = None, False

        # prune windows
        while self.samples and t - self.samples[0][0] > cfg.window_s:
            self.samples.popleft()
        for dq, w in ((self.long_blinks, cfg.window_s), (self.nods, cfg.window_s),
                      (self.yawns, cfg.yawn_window_s)):
            while dq and t - dq[0] > w:
                dq.popleft()

        tot = sum(s[1] for s in self.samples)
        perclos = (sum(s[1] for s in self.samples if s[2]) / tot) * min(1.0, tot / 15.0) if tot > 0 else 0.0

        s_p = _clamp(perclos / cfg.perclos_full)
        s_b = _clamp(len(self.long_blinks) / cfg.long_blink_full)
        s_y = _clamp(len(self.yawns) / cfg.yawn_full)
        s_n = _clamp(len(self.nods) / cfg.nod_full)
        comps = {"EYE CLOSURE RATE": 0.40 * s_p, "LONG BLINKS": 0.20 * s_b,
                 "YAWNING": 0.15 * s_y, "HEAD NODDING": 0.25 * s_n}

        # recovery: fade the score once the driver has been alert for a while
        alert_s = t - self.last_event_t
        recovering = alert_s > cfg.recover_s
        fade = max(0.0, 1.0 - (alert_s - cfg.recover_s) / cfg.fade_s) if recovering else 1.0
        raw = 100.0 * sum(comps.values()) * fade

        floor = 0.0
        if closure >= cfg.crit_closure_s:
            floor = 90.0
        elif closure >= cfg.warn_closure_s:
            floor = 60.0
        if down_s >= cfg.head_down_crit_s:
            floor = max(floor, 85.0)
        elif down_s >= cfg.head_down_warn_s:
            floor = max(floor, 60.0)

        if dt > 0:
            if raw > self.score:
                tau = cfg.rise_tau
            else:
                tau = cfg.fall_tau_recover if recovering else cfg.fall_tau
            self.score += (raw - self.score) * (1 - math.exp(-dt / tau))
        self.score = max(self.score, floor)

        # levels rise instantly, step down one at a time after a hold
        th, lvl, raised = cfg.thresholds, self.level, False
        while lvl < 3 and self.score >= th[lvl + 1]:
            lvl += 1
            raised = True
        if raised:
            self.below_since = None
        elif lvl > 0 and self.score < th[lvl] - cfg.hyst:
            if self.below_since is None:
                self.below_since = t
            elif t - self.below_since >= cfg.recovery_hold[lvl]:
                lvl -= 1
                self.below_since = None
        else:
            self.below_since = None
        self.level = lvl

        if closure >= cfg.warn_closure_s:
            reason = "EYES CLOSED"
        elif down_s >= cfg.head_down_warn_s:
            reason = "HEAD DOWN"
        else:
            reason = max(comps, key=comps.get)

        st.score, st.level, st.reason = self.score, lvl, reason
        st.closure_s, st.head_down_s, st.perclos = closure, down_s, perclos
        st.long_blinks, st.yawns, st.nods = len(self.long_blinks), len(self.yawns), len(self.nods)
        if st.face_lost:
            st.level, st.reason = max(lvl, 2), "DRIVER NOT DETECTED"
        return st