import argparse
import asyncio
import json
import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse
from core.paths import resource_path
from core.pipeline import Pipeline

ap = argparse.ArgumentParser()
ap.add_argument("--cam", type=int, default=0)
ap.add_argument("--port", type=int, default=8765)
args = ap.parse_args()

pipe = Pipeline(args.cam)
pipe.start()
app = FastAPI()
INDEX = resource_path("ui/web/index.html")


@app.get("/")
def index():
    return FileResponse(INDEX, headers={"Cache-Control": "no-store"})


@app.get("/video")
async def video():
    async def gen():
        last = 0
        while True:
            jpg, fid = pipe.get_frame()
            if jpg is None or fid == last:
                await asyncio.sleep(0.008)
                continue
            last = fid
            yield (b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: "
                   + str(len(jpg)).encode() + b"\r\n\r\n" + jpg + b"\r\n")
    return StreamingResponse(gen(), media_type="multipart/x-mixed-replace; boundary=frame")


@app.get("/events")
async def events():
    async def gen():
        while True:
            yield "data: " + json.dumps(pipe.get_state()) + "\n\n"
            await asyncio.sleep(0.05)
    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache"})


@app.post("/api/calibrate")
def calibrate():
    pipe.request_calibration()
    return {"ok": True}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")