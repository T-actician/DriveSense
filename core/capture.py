import threading
import cv2


class Camera:
    def __init__(self, index=0, width=640, height=480, fps=30):
        self.cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.cap.set(cv2.CAP_PROP_FPS, fps)
        self._frame, self._id = None, 0
        self._lock = threading.Lock()
        self._run = False

    def start(self):
        if not self.cap.isOpened():
            raise RuntimeError("Camera not opened. Try another index with --cam 1")
        self._run = True
        threading.Thread(target=self._loop, daemon=True).start()
        return self

    def _loop(self):
        while self._run:
            ok, f = self.cap.read()
            if ok:
                with self._lock:
                    self._frame, self._id = f, self._id + 1

    def read(self):
        with self._lock:
            if self._frame is None:
                return 0, None
            return self._id, self._frame.copy()

    def stop(self):
        self._run = False
        self.cap.release()