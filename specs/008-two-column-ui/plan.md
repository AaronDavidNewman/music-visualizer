# Implementation Plan: Two-Column UI

**Branch**: `008-two-column-ui` (no git branch created; spec directory name only) | **Date**: 2026-10-06 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/008-two-column-ui/spec.md`

## Summary

The page becomes two columns. The **left** column holds the audio file chooser, then the job progress/error messages, then the result (summary text, notice, frame preview and playback controls). The **right** column holds the settings and the "Create frames" button. Window size, frame rate and window spacing share one wrapping row. Each setting's helper line is replaced by an info button that opens a popover with the same text; validation errors and the below-minimum spacing notice stay inline. Below a narrow-window breakpoint the columns stack.

The work is frontend only. Technically:

- `UploadForm.vue` is split in two. A new `FilePicker.vue` owns the chooser UI, and a new `SettingsForm.vue` owns the settings, their validation and the submit button. `App.vue` holds the chosen file and its sample rate (the one piece of state both halves need) and lays out the two columns.
- A new `InfoPopover.vue` uses the browser's native popover (`popover` attribute plus `popovertarget`), which provides Escape, click-outside dismissal and one-open-at-a-time with no code. A small pure helper, `utilities/popover.ts`, places the popover beside its button and keeps it inside the window.
- No backend change, no new dependency, and the request sent to the server is identical (FR-014, SC-008).

## Technical Context

**Language/Version**: TypeScript 5.5, Vue 3.5 single-file components (`<script setup>`); the backend (Python 3.10) is unchanged

**Primary Dependencies**: Existing only (vue, vite, vitest, vue-tsc). The native Popover API is used, so no popover or UI library is added. See research Decisions 1 and 2.

**Storage**: N/A

**Testing**: vitest for the pure logic (popover placement and clamping, and the explanation text for each setting, which moves out of the template into a testable function). The test environment is Node with no DOM, and the plan adds none, so component behavior (layout, popover open/close, keyboard use, stacking) is checked by the manual and browser-driven steps in [quickstart.md](quickstart.md). `npm run typecheck` and `npm run build` must stay clean. Existing frontend and backend tests must pass unchanged.

**Target Platform**: Modern desktop browsers (Chromium, Firefox, Safari from 2024 onward, where the Popover API is available); phone-width windows through the stacked fallback.

**Project Type**: Web application: existing `backend/` and `frontend/` projects; only `frontend/` changes.

**Performance Goals**: None beyond not regressing. Opening a popover is instant and the layout adds no scripting on the frame-playback path.

**Constraints**: The preview keeps its 3:2 proportions and its 660 px maximum width; the settings keep their defaults, ranges, validation messages and the default-spacing recalculation; no horizontal scroll at 360 px.

**Scale/Scope**: Three new components (`FilePicker`, `SettingsForm`, `InfoPopover`), one new helper module with tests, edits to `App.vue`, and removal of `UploadForm.vue` (its content moves into the two new components). The README's UI description is updated.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` is still the unfilled template, with no ratified principles, so no gates apply. Result: **PASS (no constraints defined)**. The plan adds no dependency and no new project. Re-check after Phase 1: **PASS**.

## Project Structure

### Documentation (this feature)

```text
specs/008-two-column-ui/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── ui-layout.md
├── checklists/
│   └── requirements.md
└── tasks.md             # created by /speckit-tasks
```

### Source Code (repository root)

```text
frontend/src/
├── App.vue                          # owns file + sample rate; two-column grid; left: picker, status, result; right: settings
├── components/
│   ├── FilePicker.vue               # NEW: chooser, file name/size, file error (from UploadForm)
│   ├── SettingsForm.vue             # NEW: settings, row of three, submit (from UploadForm)
│   ├── InfoPopover.vue              # NEW: info button + native popover, placed and clamped
│   ├── FramePlayer.vue              # unchanged
│   └── UploadForm.vue               # REMOVED (split into the two above)
└── utilities/
    ├── popover.ts                   # NEW: popoverPosition(anchor, popover, viewport) -> {left, top}
    ├── popover.test.ts              # NEW
    ├── help.ts                      # NEW: explanation text for each setting (moved from the template)
    └── help.test.ts                 # NEW

README.md                            # UI description updated
```

**Structure Decision**: Splitting `UploadForm` is what makes the two columns possible, because the chooser and the settings now sit in different columns while still forming one form submission. `App.vue` holds the chosen `File` and its sample rate and passes them down; `SettingsForm` emits `submit` with the file and settings exactly as `UploadForm` did, so `submitJob` and the API are unchanged. Explanation strings move to `utilities/help.ts` because they now feed a popover and are worth testing without a DOM, and the spacing one depends on the live step hint.

## Complexity Tracking

No constitution violations. Nothing to justify.
