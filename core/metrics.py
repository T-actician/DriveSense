import math
from dataclasses import dataclass
import numpy as np

RIGHT_EYE = [33, 160, 158, 133, 153, 144]
LEFT_EYE = [362, 385, 387, 263, 373, 380]


@dataclass
class FrameMetrics:
    face: bool = False
    ear_l: float = 0.0
    ear_r: float = 0.0
    ear: float = 0.0
    mar: float = 0.0
    pitch: float = 0.0
    yaw: float = 0.0
    roll: float = 0.0


def _d(a, b):
    return float(np.linalg.norm(a - b))


def _ear(pts, idx):
    p1, p2, p3, p4, p5, p6 = (pts[i] for i in idx)
    return (_d(p2, p6) + _d(p3, p5)) / (2.0 * _d(p1, p4) + 1e-6)


def _mar(pts):
    return _d(pts[13], pts[14]) / (_d(pts[78], pts[308]) + 1e-6)


def _head_pose(mat):
    R = np.array(mat[:3, :3], dtype=np.float64)
    R = R / (np.linalg.norm(R, axis=0) + 1e-9)
    sy = math.hypot(R[0, 0], R[1, 0])
    pitch = math.degrees(math.atan2(R[2, 1], R[2, 2]))
    yaw = math.degrees(math.atan2(-R[2, 0], sy))
    roll = math.degrees(math.atan2(R[1, 0], R[0, 0]))
    if pitch > 90:
        pitch -= 180
    elif pitch < -90:
        pitch += 180
    return pitch, yaw, roll


def compute(pts, mat) -> FrameMetrics:
    if pts is None:
        return FrameMetrics()
    el, er = _ear(pts, LEFT_EYE), _ear(pts, RIGHT_EYE)
    p, y, r = _head_pose(mat) if mat is not None else (0.0, 0.0, 0.0)
    return FrameMetrics(True, el, er, (el + er) / 2, _mar(pts), p, y, r)