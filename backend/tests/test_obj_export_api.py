"""The 3D export through ``POST /api/jobs`` and ``GET /api/jobs/{job_id}/obj`` (feature 045)."""

import importlib.util
import io
import zipfile
from pathlib import Path

import numpy as np
import pytest

from app.config import settings
from app.services.image_types import IMAGE_TYPES

from .test_jobs_api import client, leftovers, note_tone, wav_bytes  # noqa: F401
from .test_peak_tile_colors_api import TONE_NOTE, all_frames, post
from .test_resolution_api import tiny

_READER = Path(__file__).resolve().parents[2] / "specs" / "045-obj-export-mode" / "tools" / "read_obj.py"
_spec = importlib.util.spec_from_file_location("read_obj", _READER)
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
read_obj = _module.read_obj

NOT_AVAILABLE = "The 3D export is only available for Contour and Chromatic Wireframe."
NOT_BOOL = "The 3D export must be true or false."
NO_EXPORT = "No 3D export was made for this render."
OTHER_TYPES = [name for name in IMAGE_TYPES if name not in ("contour", "chromatic-wireframe")]


@pytest.fixture
def export_client(client, tmp_path, monkeypatch):
    """The client with the output folder in the test's folder (the ZIP is made there, not in the real output folder)."""
    monkeypatch.setattr(settings, "output_dir", tmp_path / "output")
    return client


def song(seconds: float = 2.0) -> bytes:
    """A steady tone with a clear change in it, so the notes and the beat are not all the same."""
    return wav_bytes(0.3 * np.concatenate([note_tone(TONE_NOTE, seconds / 2), note_tone(TONE_NOTE + 7, seconds / 2)]))


def make(client, image_type: str, export=True, **fields):
    form = {"image_type": image_type, **fields}
    if export is not None:
        form["export_obj"] = export if isinstance(export, str) else ("true" if export else "false")
    return post(client, song(), **form)


def archive(client, job) -> zipfile.ZipFile:
    r = client.get(job["obj_url"])
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "application/zip"
    assert "obj.zip" in r.headers["content-disposition"]
    return zipfile.ZipFile(io.BytesIO(r.content))


def size_of(pack: zipfile.ZipFile, name: str) -> tuple[int, int]:
    vertices, faces, _ = read_obj(pack.read(name).decode("ascii"))
    return len(vertices), len(faces)


# ---- the contour --------------------------------------------------------------------------------------------------------------------------


def test_a_contour_job_with_the_export_answers_with_the_address_and_the_zip_has_one_file_per_frame(export_client):
    r = make(export_client, "contour")
    assert r.status_code == 200, r.text
    job = r.json()
    assert job["export_obj"] is True and job["obj_url"] == f"/api/jobs/{job['job_id']}/obj"
    pack = archive(export_client, job)
    assert pack.namelist() == [f"frame_{i:06d}.obj" for i in range(job["frame_count"])]
    for name in pack.namelist():
        assert size_of(pack, name) == (84, 66), name


def test_the_files_are_numbered_like_the_pictures(export_client):
    job = make(export_client, "contour").json()
    pack = archive(export_client, job)
    for i in (0, job["frame_count"] - 1):
        assert export_client.get(job["frame_url_template"].replace("{index}", str(i))).status_code == 200
        assert f"frame_{i:06d}.obj" in pack.namelist()


# ---- the wireframe ------------------------------------------------------------------------------------------------------------------------


def test_a_wireframe_job_with_the_export_has_lines_of_12_points_and_a_window_of_12_lines(export_client):
    job = make(export_client, "chromatic-wireframe").json()
    assert job["export_obj"] is True and job["frame_count"] >= 12
    pack = archive(export_client, job)
    assert pack.namelist() == [f"frame_{i:06d}.obj" for i in range(job["frame_count"])]
    assert size_of(pack, "frame_000000.obj") == (12, 0)
    assert size_of(pack, "frame_000005.obj") == (72, 55)
    for i in range(11, job["frame_count"]):
        assert size_of(pack, f"frame_{i:06d}.obj") == (144, 121), i


# ---- off, and the other pictures ----------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("image_type", ["contour", "chromatic-wireframe"])
@pytest.mark.parametrize("export", [None, False, "0", "FALSE", " false "])
def test_without_the_export_there_are_no_files_and_the_answer_says_so(export_client, image_type, export):
    r = make(export_client, image_type, export=export)
    assert r.status_code == 200, r.text
    job = r.json()
    assert job["export_obj"] is False and job["obj_url"] is None
    assert not (settings.frames_temp_dir / job["job_id"] / "obj").exists()
    missing = export_client.get(f"/api/jobs/{job['job_id']}/obj")
    assert missing.status_code == 404 and missing.json()["detail"] == NO_EXPORT


@pytest.mark.parametrize("image_type", ["contour", "chromatic-wireframe"])
def test_the_pictures_are_the_same_with_the_export_on_and_off(export_client, image_type):
    on = make(export_client, image_type, export=True).json()
    off = make(export_client, image_type, export=False).json()
    assert on["frame_count"] == off["frame_count"]
    assert all_frames(export_client, on) == all_frames(export_client, off)


@pytest.mark.parametrize("image_type", OTHER_TYPES)
def test_the_export_is_refused_for_the_other_pictures_before_any_work_is_done(export_client, image_type):
    for word in ("true", "1", "TRUE"):
        r = post(export_client, tiny(), image_type=image_type, export_obj=word)
        assert r.status_code == 400 and r.json()["detail"] == NOT_AVAILABLE, (image_type, word)
        assert leftovers() == []


@pytest.mark.parametrize("image_type", OTHER_TYPES)
def test_export_off_is_accepted_for_the_other_pictures_and_reported(export_client, image_type):
    r = post(export_client, tiny(), image_type=image_type, export_obj="false")
    assert r.status_code == 200, r.text
    assert r.json()["export_obj"] is False and r.json()["obj_url"] is None


@pytest.mark.parametrize("word", ["maybe", "yes", "", "2", "tru"])
def test_a_value_that_is_not_true_or_false_is_refused(export_client, word):
    for image_type in ("contour", "decay"):
        r = post(export_client, tiny(), image_type=image_type, export_obj=word)
        assert r.status_code == 400 and r.json()["detail"] == NOT_BOOL, (image_type, word)
        assert leftovers() == []


def test_the_answer_of_every_picture_has_the_two_keys(export_client):
    for image_type in IMAGE_TYPES:
        job = post(export_client, tiny(), image_type=image_type).json()
        assert job["export_obj"] is False and job["obj_url"] is None, image_type


# ---- the download -------------------------------------------------------------------------------------------------------------------------


def test_a_bad_job_number_is_not_found(export_client):
    for bad in ("nope", "0" * 31, "A" * 32, "../x"):
        r = export_client.get(f"/api/jobs/{bad}/obj")
        assert r.status_code == 404 and r.json()["detail"] in ("Render not found.", "Not Found"), bad


def test_a_job_that_does_not_exist_has_no_export(export_client):
    r = export_client.get("/api/jobs/" + "0" * 32 + "/obj")
    assert r.status_code == 404 and r.json()["detail"] == NO_EXPORT


def test_asking_for_the_zip_twice_gives_the_same_bytes_and_one_archive(export_client):
    job = make(export_client, "contour").json()
    first = export_client.get(job["obj_url"]).content
    second = export_client.get(job["obj_url"]).content
    assert first == second
    assert [p.name for p in (settings.output_dir / job["job_id"]).iterdir()] == ["obj.zip"]


@pytest.mark.parametrize("image_type", ["contour", "chromatic-wireframe"])
def test_the_same_music_and_settings_give_identical_files(export_client, image_type):
    a = archive(export_client, make(export_client, image_type).json())
    b = archive(export_client, make(export_client, image_type).json())
    assert a.namelist() == b.namelist()
    for name in a.namelist():
        assert a.read(name) == b.read(name), name


def test_a_bad_setting_with_the_export_leaves_nothing_behind(export_client):
    r = post(export_client, song(), image_type="contour", export_obj="true", colormap="nope")
    assert r.status_code == 400
    assert leftovers() == []
