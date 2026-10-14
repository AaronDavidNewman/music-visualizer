# Implementation Plan: Grouped, Collapsible Settings

**Branch**: `020-grouped-settings-ui` (no git branch created; spec directory name only) | **Date**: 2026-10-14 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/020-grouped-settings-ui/spec.md`

## Summary

The settings form becomes an ordered list of **titled, individually collapsible groups**, each laid out **two controls to a row** (an odd last control takes the whole row): the top group (Window size, Frame rate, Window spacing), Colormap, Image type, **the group of the chosen image type** (Tiles / Contour: Threshold, Notes; Blended Tiles: Threshold, Notes, Blend width; Circles: Movement, Radius, Resize by volume, Memory, Notes), **Data smoothing** (Smoothing window, Smoothing) and **Image smoothing** (Oversampling, Interpolate; not for Circles). A control that does not apply to the chosen type is **not shown** (today it is greyed out). Four controls are renamed: Unit to **Movement**, Size to **Radius**, Circles per frame to **Notes**, Resolution to **Oversampling**, in the form, the info texts, the validation messages and the result summary. **Radius becomes a real radius** (clarification): a whole number of pixels, 4 to 8, default 4, replacing the circumference of 25 to 50, which also changes the request field (`circle_size` becomes `circle_radius`) and the circle drawing.

Work by area:

- **Frontend (the bulk)**: a new pure module `utilities/groups.ts` (the group definitions: id, title by image type, its controls in order, when it is shown, the open/closed state helpers, which group a control belongs to) that the form and the tests share; a new component `components/SettingsGroup.vue` (a native `<details>`/`<summary>` section with a "needs attention" mark and a flex body whose children are laid out two to a row by CSS); `SettingsForm.vue` rewritten to put every existing control into its group, hide inapplicable controls with `v-if` instead of `disabled`, keep one open-state map, and add a test-friendly optional prop for the starting image type; sliders in half-width cells show their readout in the label row so that nothing is cut off; the renames in `help.ts`, `validation.ts` (messages, `CIRCLE_RADIUS_RANGE` 4 to 8, default 4, `validateCircleRadius`, `formatCircleRadius`), `api.ts` (`circle_radius` / `circleRadius`) and the summary in `App.vue`.
- **Backend (the Radius change)**: `circles.py` replaces the size setting by a **radius** (`MIN/MAX/DEFAULT_CIRCLE_RADIUS` 4/8/4, `check_circle_radius`, message `The circle radius must be a whole number from 4 to 8.`) and draws discs of exactly that radius (times the resize factor 1 to 3); `circle_radius()` (size / 2 pi) goes; `frame_rendering.write_frames` and the router take `circle_radius` (field `circle_radius`, response key `circle_radius`, `circle_size` gone; an old client that still sends `circle_size` is ignored like any unknown form field); the messages of the renamed settings follow the new names (`The circle movement must be a whole number from 1 to 10.`, `The oversampling must be a whole number from 1 to 5.`); the field names `circle_unit`, `circle_notes`, `resolution` do not change.
- **Tests**: backend tests that used the size follow the radius (checks, refusals, disc radii, the covered area, the five exact-response-key tests); frontend: the group model (every control in exactly one group, the groups of each image type, rows of two, odd last full width, collapse keeps values), the rendered form for every image type (through the starting-type prop), the old names gone, source guards for the layout CSS and the accessibility attributes.
- **Docs**: README (the page description and the circles/resolution paragraphs), amendment notes on the 016 and 019 documents that name the old controls, and this feature's contract.

Worth knowing: the layout cannot be seen in a browser with the tools of this project (no browser, no DOM test environment, and adding one would be a new dependency), so the **page is verified by pure-logic tests, server-side rendering of the form and source guards**, and the visual check (SC-004, the half-width sliders) is left as a manual step in the quickstart; frames of every image type except the circles' radius setting are unchanged (the four reference hashes, and for circles only the radius setting changes: the discs have the radius that is set, and the default of 4 px is within 0.02 px of the old default).

## Technical Context

**Language/Version**: TypeScript 5.5 / Vue 3.5 (frontend), Python 3.10 (backend `.venv`)

**Primary Dependencies**: Existing only: Vue, vitest, vue-tsc, Vite; numpy, Pillow, FastAPI. No new dependency (no DOM test library is added).

**Storage**: N/A. The open or closed state of the groups lives in memory for the page's life (not remembered between visits).

**Testing**: vitest (pure group model, SSR rendering of the form with each image type, source guards for CSS and accessibility markup) and pytest (the radius setting, the renamed messages, response keys).

**Target Platform**: Local developer machine, modern desktop browser; the settings column is 30 rem wide on a wide page and the page width on a narrow one.

**Project Type**: Web application: existing `backend/` and `frontend/` projects.

**Performance Goals**: None new. Circles drawing time is unchanged (the discs are the same size as before).

**Constraints**: Every control exactly once in the form; two per row, odd last full width; groups collapse independently and never lose a value; hidden controls keep their values and are still sent; frames of all other settings byte-identical to before (four reference hashes); no old name (Unit, Size, Circles per frame, Resolution) in the form, info texts, summary or client messages.

**Scale/Scope**: One new component, one new utilities module, a rewritten form template (about 20 controls in 6 groups), edits to four more frontend files plus tests; backend edits to three files plus tests; README.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` is still the unfilled template, with no ratified principles, so no gates apply. Result: **PASS (no constraints defined)**. No new dependency. Re-check after Phase 1: **PASS**.

## Project Structure

### Documentation (this feature)

```text
specs/020-grouped-settings-ui/
├── plan.md              # This file
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/
│   └── settings-ui.md   # Phase 1: the groups, the rows, the names, and the radius change in the API
└── tasks.md             # /speckit-tasks (not created by /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── services/
│   │   ├── circles.py              # radius instead of size; discs of exactly that radius
│   │   └── frame_rendering.py      # circle_radius argument
│   └── routers/jobs.py             # circle_radius field, parser, response key; renamed messages
└── tests/                          # test_circles*.py, the five exact-key tests, resolution/unit messages

frontend/
└── src/
    ├── api.ts                      # circle_radius / circleRadius
    ├── App.vue                     # summary lines with the new names
    ├── components/
    │   ├── SettingsGroup.vue       # NEW: collapsible titled group with a flex body
    │   └── SettingsForm.vue        # the controls placed in the groups
    └── utilities/
        ├── groups.ts               # NEW: the group model (pure)
        ├── help.ts                 # renamed controls, radius help
        └── validation.ts           # radius range, messages, formats
        (plus the .test.ts files of each)
README.md
```

**Structure Decision**: Existing web-application layout. The group model is a pure TypeScript module so that it can be tested in the project's node-only vitest setup; the component only renders it.

## Complexity Tracking

> No Constitution Check violations to justify.
