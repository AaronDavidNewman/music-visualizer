"""Print the shapes and element kinds of the arrays that the functions of backend/app really receive and return during one job of each image type.

The array documentation is written from this table (and from reading the code for meaning, ranges and units), so a shape in a docstring is one that was seen.

    python shape_probe.py                  every module, all 8 image types
    python shape_probe.py decay            only that image type
    python shape_probe.py --module rhythm  only the modules whose name contains the text

Arrays inside a tuple, a list or an attribute of an object (a data class) are shown as ``name[i]`` or ``name.attribute``.
"""

import sys
import tempfile
import threading
from collections import defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[2] / "backend"))

from fastapi.testclient import TestClient  # noqa: E402

import verify_frames  # noqa: E402
from app.config import settings  # noqa: E402
from app.main import app  # noqa: E402
from app.services.image_types import IMAGE_TYPES  # noqa: E402

APP = str((HERE.parents[2] / "backend" / "app").resolve()).lower()
MAX_SHAPES = 4  # distinct shapes shown for one array of one function


def describe(value, name: str, out: list[tuple[str, str]], depth: int = 0) -> None:
    """Append ``(name, "dtype (shape)")`` for each array found in ``value``."""
    if isinstance(value, np.ndarray):
        out.append((name, f"{value.dtype} {tuple(value.shape)}"))
    elif isinstance(value, (tuple, list)) and depth < 2 and 0 < len(value) <= 8 and any(isinstance(v, np.ndarray) for v in value):
        for i, item in enumerate(value):
            describe(item, f"{name}[{i}]", out, depth + 1)
    elif depth < 1 and hasattr(value, "__dataclass_fields__"):
        for field in value.__dataclass_fields__:
            attribute = getattr(value, field, None)
            if isinstance(attribute, np.ndarray):
                out.append((f"{name}.{field}", f"{attribute.dtype} {tuple(attribute.shape)}"))


def probe_one(image_type: str, audio: bytes, table: dict[tuple[str, str, str], dict[str, int]]) -> None:
    lock = threading.Lock()
    cache: dict[object, str | None] = {}

    def module_of(code) -> str | None:
        if code in cache:
            return cache[code]
        path = code.co_filename.lower()
        name = path[len(APP) + 1 :].replace("\\", "/").removesuffix(".py") if path.startswith(APP) else None
        cache[code] = name
        return name

    def profiler(frame, event, arg):
        if event not in ("call", "return"):
            return
        module = module_of(frame.f_code)
        if module is None:
            return
        code = frame.f_code
        function = code.co_name
        if function.startswith("<"):
            return
        found: list[tuple[str, str]] = []
        if event == "call":
            names = code.co_varnames[: code.co_argcount + code.co_kwonlyargcount]
            for variable in names:
                if variable in frame.f_locals:
                    describe(frame.f_locals[variable], variable, found)
            role = "in"
        else:
            describe(arg, "return", found)
            role = "out"
        if found:
            with lock:
                for name, shape in found:
                    table[(module, function, f"{role} {name}")][f"{image_type}: {shape}"] += 1

    with tempfile.TemporaryDirectory() as tmp:
        settings.audio_temp_dir = Path(tmp) / "audio"
        settings.frames_temp_dir = Path(tmp) / "frames"
        client = TestClient(app)
        threading.setprofile(profiler)
        sys.setprofile(profiler)
        try:
            response = client.post(
                "/api/jobs",
                files={"file": ("probe.wav", audio, "audio/wav")},
                data={"window_size": "4096", "frame_rate": "10", "colormap": "viridis", "image_type": image_type},
            )
        finally:
            sys.setprofile(None)
            threading.setprofile(None)
        assert response.status_code == 200, response.text


def main() -> None:
    args = sys.argv[1:]
    module_filter = ""
    if "--module" in args:
        module_filter = args[args.index("--module") + 1]
        args = [a for i, a in enumerate(args) if a != "--module" and (i == 0 or args[i - 1] != "--module")]
    wanted = [a for a in args if not a.startswith("--")] or list(IMAGE_TYPES)
    audio = verify_frames.make_audio()
    table: dict[tuple[str, str, str], dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for image_type in wanted:
        probe_one(image_type, audio, table)
    current = None
    for (module, function, array), seen in sorted(table.items()):
        if module_filter and module_filter not in module:
            continue
        if module != current:
            print(f"\n## {module}")
            current = module
        by_shape: dict[str, list[str]] = defaultdict(list)
        for entry in seen:
            image_type, _, shape = entry.partition(": ")
            by_shape[shape].append(image_type)
        shown = sorted(by_shape.items(), key=lambda item: -len(item[1]))[:MAX_SHAPES]
        text = "; ".join(f"{shape} [{', '.join(sorted(types)) if len(types) < len(wanted) else 'all'}]" for shape, types in shown)
        more = f" (+{len(by_shape) - MAX_SHAPES} more shapes)" if len(by_shape) > MAX_SHAPES else ""
        print(f"  {function}: {array}: {text}{more}")


if __name__ == "__main__":
    main()
