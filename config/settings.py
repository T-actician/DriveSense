from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    ear_close_ratio: float = 0.35
    long_blink_s: float = 0.40
    warn_closure_s: float = 0.80
    crit_closure_s: float = 1.50
    window_s: float = 60.0
    yawn_window_s: float = 300.0
    perclos_full: float = 0.20
    long_blink_full: int = 4
    yawn_full: int = 3
    nod_full: int = 3
    yawn_mar: float = 0.50
    yawn_s: float = 1.2
    nod_deg: float = 12.0
    nod_s: float = 0.4
    head_down_warn_s: float = 2.0
    head_down_crit_s: float = 3.5
    face_lost_s: float = 3.0
    rise_tau: float = 0.8
    fall_tau: float = 10.0
    hyst: float = 5.0
    thresholds: tuple = (0, 30, 55, 80)
    # recovery
    recover_closure_s: float = 0.25
    recover_s: float = 6.0
    fade_s: float = 12.0
    fall_tau_recover: float = 4.0
    recovery_hold: tuple = (0, 8, 6, 4)