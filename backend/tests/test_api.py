import io

from fastapi.testclient import TestClient
from PIL import Image

from app.main import app

client = TestClient(app)


def test_hello():
    r = client.get("/api/hello")
    assert r.status_code == 200
    assert r.json() == {"message": "Hello, world!"}


def test_image_info():
    buf = io.BytesIO()
    Image.new("RGB", (4, 3)).save(buf, format="PNG")
    r = client.post("/api/images/info", files={"file": ("x.png", buf.getvalue(), "image/png")})
    assert r.status_code == 200
    assert r.json() == {"format": "PNG", "mode": "RGB", "width": 4, "height": 3}


def test_image_info_rejects_non_image():
    r = client.post("/api/images/info", files={"file": ("x.txt", b"nope", "text/plain")})
    assert r.status_code == 400


def test_serves_frontend_index(tmp_path, monkeypatch):
    import importlib

    from app import config, main

    (tmp_path / "index.html").write_text("<div id=app></div>")
    monkeypatch.setattr(config.settings, "frontend_dist", tmp_path)
    importlib.reload(main)
    try:
        r = TestClient(main.app).get("/")
        assert r.status_code == 200
        assert "id=app" in r.text
        assert TestClient(main.app).get("/api/hello").status_code == 200
    finally:
        monkeypatch.undo()
        importlib.reload(main)
