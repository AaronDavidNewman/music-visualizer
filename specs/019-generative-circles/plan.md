# Implementation Plan: Generative Circles

> **Amended 2026-10-14 (feature 020, grouped settings).** On the page the circles settings were renamed: **Unit** is now **Movement**, **Size** is now **Radius**, **Circles per frame** is now **Notes** (and the summary says Memory for the circle memory), all inside a **Circles** group that is shown only for Circles; the controls the type does not use are no longer greyed out but not shown. **The Size setting became a real radius**: a whole number of pixels from **4 to 8** (default 4), request field `circle_radius` with the message `The circle radius must be a whole number from 4 to 8.`, replacing the circumference of 25 to 50 pixels (`circle_size`, now ignored if sent; a radius of 3.98 to 7.96). The unit message is now `The circle movement must be a whole number from 1 to 10.`. Where this document, or its earlier amendments, say size, circumference, 25 to 50 or `circle_size`, the radius governs; the Resize by volume factor (1 to 3) applies to the radius. See `specs/020-grouped-settings-ui/`.

> **Amended 2026-10-13 (look and size of the circles).** After this feature was delivered the user asked for three changes: (1) the background is the **middle color of the colormap** (row 128 of its 256-entry table) instead of black; (2) each circle is drawn with an **opacity that falls with its age** (newest opaque, opacity (m - age) / m in a memory of m circles, so the oldest is barely visible just before it is dropped); (3) a new fourth circle setting, the **circle size** (the circumference in pixels, a whole number from 25 to 50, default 25, radius size / (2 pi)), replaces "the radius is one unit" (the unit is now only the length of a step). Where this document still says black, "radius of one unit" or "three settings", the amended spec (`spec.md`, Clarifications) governs.

**Branch**: `019-generative-circles` (no git branch created; spec directory name only) | **Date**: 2026-10-13 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/019-generative-circles/spec.md`

## Summary

A fourth image type, `circles`, draws each frame as a black picture of 252 × 168 pixels with colored circles that **wander**. In every frame the n strongest notes of that frame (n from 5 to 12, by smoothed value, ties to the lower note, notes with no energy dropped) are sorted from the strongest down; the circle of rank r is placed relative to the circle that rank r had in the previous frame, moved by an angle (30° times the note name counted from C, mirrored below octave 4) and a distance of `1 + |octave − 4|` units (the user's rule, option C), a unit being 1 to 10 pixels; places wrap around the picture, and every rank starts from the middle. The circle takes the color of the selected colormap at the note's strength (the tiles' scale) and goes into a circular memory of the last 100 to 500 circles, which is drawn in full in every frame, oldest first. The three new settings are the unit (default 4), the memory (default 300) and the circles per frame (default 8). Interpolate, Resolution, Notes, Threshold and Blend width have no meaning for circles: they are accepted and ignored, and the page disables them.

Work by area:

- **Backend**: a new module `app/services/circles.py` (the three settings and their checks, `note_move`, the frame-by-frame placement with a `deque(maxlen=)` memory, the drawing with Pillow `ImageDraw.ellipse`, and the writer, which saves on a few threads); `IMAGE_TYPES` gains `circles`; `write_frames` gets the three arguments and a `circles` branch that returns before the grid pipeline; the router gets three fields and three response keys. The tiles, blended and contour code is not touched.
- **Frontend**: a fourth image type, three sliders shown only for circles, five controls disabled for circles, help texts, summary lines and the fields in `api.ts`, with their tests.
- **Tests**: the move of every note against the user's examples and an independent computation from the frequency; the placement frame by frame; the choice, the color, the memory; the API; the page. The tiles, blended and contour output must equal the four reference hashes.
- **Docs**: README.

A prototype (research.md) reproduced the examples (F5: 150° and 2 units, F3: 210° and 2 units, A4: 270° and 1 unit) and measured the work at about 2 ms a frame at the largest settings (placement 0.03 ms, drawing 0.5 ms, saving 1.4 ms), so a 1,800-frame job takes a few seconds.

Worth knowing: for circles the angle and distance come from the note's real name and octave, not from its grid cell (the application's grid starts at A, the request counts from C); the notes are chosen **per frame**, unlike the file-wide choice of feature 017; places wrap but circles near an edge are only cut off by it, not drawn again on the opposite side. The user's colormap edit (the lists in `colormaps.py` and `validation.ts` disagree, and the backend default `hot` is not in its list) is outside this feature and makes the whole backend suite fail at import until it is settled, so verification here uses the same temporary default as in feature 018.

## Technical Context

**Language/Version**: Python 3.10 (backend `.venv`), TypeScript 5.5 / Vue 3.5 (frontend)

**Primary Dependencies**: Existing numpy, Pillow 12.3 (`ImageDraw`), matplotlib (the colormap table), FastAPI; Vue, vitest. No new dependency.

**Storage**: N/A. Same temp directories and file names; circle frames are RGB PNGs.

**Testing**: pytest and vitest. New: `test_circles.py` (checks, the move, the placement, the memory), `test_circles_rendering.py` (`write_frames` and the pictures), `test_circles_api.py`; the existing exact-response-key tests gain the three keys; `test_image_types.py` and the image-type API tests already derive their lists from `IMAGE_TYPES`. vitest: ranges, validation, readouts, help, the conditional controls, the disabled rule, the summary. The colormap-list-tolerant helpers are used; no test states a number of contour levels.

**Target Platform**: Local developer machine, modern desktop browser.

**Project Type**: Web application: existing `backend/` and `frontend/` projects.

**Performance Goals**: A 300-frame circles job with 12 circles per frame, a memory of 500 and a unit of 10 within one minute (SC-006); measured about 2 ms a frame.

**Constraints**: Deterministic output; the same size, frame count, timing and file names as the other types; tiles, blended and contour files byte-identical to before (four reference hashes); placement arithmetic exact to the pixel.

**Scale/Scope**: One new backend module (~150 lines), a branch in `frame_rendering.py`, a tuple entry, three fields in `jobs.py`; frontend edits to five files plus tests; README.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` is still the unfilled template, with no ratified principles, so no gates apply. Result: **PASS (no constraints defined)**. No new dependency. Re-check after Phase 1: **PASS**.

## Project Structure

### Documentation (this feature)

```text
specs/019-generative-circles/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── circles-api.md
├── checklists/
│   └── requirements.md
└── tasks.md             # created by /speckit-tasks
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── services/
│   │   ├── circles.py               # NEW: settings, note_move(), plan_circles(), write_circle_frames()
│   │   ├── image_types.py           # IMAGE_TYPES = ("tiles", "blended", "contour", "circles")
│   │   └── frame_rendering.py       # write_frames(circle_unit=, circle_memory=, circle_notes=): the circles branch
│   └── routers/jobs.py              # + three fields, parsers, response keys
└── tests/
    ├── test_circles.py              # NEW
    ├── test_circles_rendering.py    # NEW
    ├── test_circles_api.py          # NEW
    └── test_*_api.py                # exact response keys + the three circle keys

frontend/src/
├── api.ts                           # + circleUnit, circleMemory, circleNotes (settings, result, form fields)
├── App.vue                          # summary lines for circles, the grid lines hidden for circles
├── components/
│   ├── SettingsForm.vue             # three conditional sliders, five controls disabled for circles
│   └── SettingsForm.test.ts
└── utilities/
    ├── validation.ts                # IMAGE_TYPES + circles; ranges, validators, readouts, gridSettingsApply
    ├── validation.test.ts
    ├── help.ts                      # imageTypeHelp + Circles; three new help texts
    └── help.test.ts

README.md                            # the circles image type and its settings
```

**Structure Decision**: The circles are drawn by their own module, like the contour, so nothing that exists changes and the 84-note grid pipeline (the spread, the resolution, the threshold, the writers, the interpolation pass) is simply not entered for circles. The placement is a sequential loop over frames because each frame depends on the earlier ones; only the saving of the pictures goes to threads.

## Complexity Tracking

No constitution violations. Nothing to justify.
