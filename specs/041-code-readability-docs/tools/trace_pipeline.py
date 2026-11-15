"""Print, for one job of each image type, the order in which the functions of backend/app are FIRST called.

It is the independent oracle for the "Order of operations" of a module and for the overview of the image types: compare what is written with what runs.

    python trace_pipeline.py                 one list for each of the 8 image types (the validation helpers `check_*` and `_check_*` and dunder methods are left out)
    python trace_pipeline.py decay           only that type
    python trace_pipeline.py --all           also the validation helpers and everything else
"""

import sys
import tempfile
import threading
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[2] / "backend"))

from fastapi.testclient import TestClient  # noqa: E402

import verify_frames  # noqa: E402
from app.config import settings  # noqa: E402
from app.main import app  # noqa: E402
from app.services.image_types import IMAGE_TYPES  # noqa: E402

APP = str((HERE.parents[2] / "backend" / "app").resolve()).lower()
SHOW_ALL = "--all" in sys.argv


def trace_one(image_type: str, audio: bytes) -> list[str]:
    seen: dict[tuple[str, str], int] = {}
    order: list[str] = []
    lock = threading.Lock()
    cache: dict[object, str | None] = {}

    def module_of(code) -> str | None:
        if code in cache:
            return cache[code]
        path = code.co_filename.lower()
        name = None
        if path.startswith(APP):
            name = path[len(APP) + 1 :].replace("\\", "/").removesuffix(".py")
        cache[code] = name
        return name

    def profiler(frame, event, arg):
        if event != "call":
            return
        module = module_of(frame.f_code)
        if module is None:
            return
        function = frame.f_code.co_name
        if function.startswith("<"):
            return
        if not SHOW_ALL and (function.startswith("check_") or function.startswith("_check") or (function.startswith("__") and function.endswith("__"))):
            return
        key = (module, function)
        with lock:
            if key not in seen:
                seen[key] = len(order)
                order.append(f"{module}.{function}")

    with tempfile.TemporaryDirectory() as tmp:
        settings.audio_temp_dir = Path(tmp) / "audio"
        settings.frames_temp_dir = Path(tmp) / "frames"
        client = TestClient(app)
        threading.setprofile(profiler)
        sys.setprofile(profiler)
        try:
            response = client.post(
                "/api/jobs",
                files={"file": ("trace.wav", audio, "audio/wav")},
                data={"window_size": "4096", "frame_rate": "10", "colormap": "viridis", "image_type": image_type},
            )
        finally:
            sys.setprofile(None)
            threading.setprofile(None)
        assert response.status_code == 200, response.text
    return order


def main() -> None:
    wanted = [a for a in sys.argv[1:] if not a.startswith("--")] or list(IMAGE_TYPES)
    audio = verify_frames.make_audio()
    for image_type in wanted:
        order = trace_one(image_type, audio)
        print(f"\n=== {image_type}: {len(order)} functions, in the order of their first call")
        for number, name in enumerate(order, 1):
            print(f"  {number:3d}. {name}")


if __name__ == "__main__":
    main()
