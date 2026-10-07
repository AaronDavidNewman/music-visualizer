---

description: "Task list for Two-Column UI"
---

# Tasks: Two-Column UI

**Input**: Design documents from `/specs/008-two-column-ui/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ui-layout.md, quickstart.md

**Tests**: Included where the plan calls for them: vitest for the two pure helpers (popover placement, explanation text). The frontend has no DOM test environment and this plan adds none (research Decision 7), so layout and popover behavior are checked in a real browser by the steps in `quickstart.md`. The backend is not changed and is only re-run.

**Organization**: Tasks are grouped by user story. Paths are relative to the repository root. All source changes are in `frontend/src/`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1, US2, US3 or US4

## Phase 1: Setup

- [x] T001 Run `npm test`, `npm run typecheck` and `npm run build` in `frontend/`, and `pytest` in `backend/`, to confirm a green baseline before changing anything; note the test counts

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Split `UploadForm.vue` into the chooser and the settings, with the file shared through `App.vue`, and no visible change yet. Every story edits one of these pieces.

- [x] T002 [P] Create `frontend/src/components/FilePicker.vue` from the file-chooser part of `frontend/src/components/UploadForm.vue`. Props: `busy: boolean`, `file: File | null`. Emits: `update:file` (`File | null`) and `update:sampleRate` (number, Hz). Move into it the "Audio file" label with the `.wav` input (disabled while `busy`), the "Choose a .wav file." prompt or the file's name and size (`formatSize`), the `validateFile` error (shown only when a file is chosen), and `onFile` with its `latestFile` ticket so a stale `readSampleRate` answer is ignored; emit `DEFAULT_SAMPLE_RATE` when the header cannot be read or the file is cleared. Move the styles these elements use
- [x] T003 [P] Create `frontend/src/components/SettingsForm.vue` from the rest of `frontend/src/components/UploadForm.vue`. Props: `busy: boolean`, `file: File | null`, `sampleRate: number`. Emits: `submit` with `(file: File, settings: JobSettings)`, the same payload as today. Move into it window size, frame rate, window spacing, brightness and smoothing with their state, validation, `canSubmit` (which now also requires `validateFile(props.file)` to be null), the default-spacing `watch` (watching window size, frame rate, `props.sampleRate` and `props.file`, replacing the spacing text only when the default is usable), `belowMinimum`, `stepHint`, and the "Create frames" button. Keep every helper line and message exactly as it is for now; defaults, ranges and the submitted `JobSettings` (smoothing rounded to two decimals) must not change
- [x] T004 Update `frontend/src/App.vue`: keep `file` (`ref<File | null>`) and `fileSampleRate` (`ref<number>(DEFAULT_SAMPLE_RATE)`), render `<FilePicker>` (with `v-model:file` and `@update:sample-rate`) and `<SettingsForm>` where `<UploadForm>` was, and make `onSubmit` accept `(file, settings)` as before. Then delete `frontend/src/components/UploadForm.vue`
- [x] T005 Run `npm test`, `npm run typecheck` and `npm run build` in `frontend/`, start the app, and confirm the page works exactly as before (choose a file, the spacing default follows the window size, frame rate and file, create frames, play)

**Checkpoint**: Same page, same behavior, now built from two form pieces.

---

## Phase 3: User Story 1 - Preview on the left, settings on the right (Priority: P1) 🎯 MVP

**Goal**: Two columns: file chooser, status and result on the left; settings and "Create frames" on the right (FR-001 to FR-004, FR-013).

**Independent Test**: Quickstart "Story 1". At 1280 px wide the chooser and preview are in the left column and every setting and the button in the right; frames created from the right update the left.

- [x] T006 [US1] In `frontend/src/App.vue` restructure the template under the `<h1>` into a layout wrapper with two columns: a left column containing `<FilePicker>`, the busy message, the error box, and the results section (heading, summary list, spacing-raised notice, `<FramePlayer>`), and a right column containing `<SettingsForm>`. Nothing from the results goes in the right column and no setting in the left
- [x] T007 [US1] In `frontend/src/App.vue` styles: widen `main` from `max-width: 48rem` to about `76rem`; make the layout wrapper a single column by default, and at `min-width: 60rem` a two-column grid with a flexible left column and a fixed right column of `30rem` (`grid-template-columns: minmax(0, 1fr) 30rem`, `align-items: start`); give both columns `min-width: 0` and a vertical gap like the old page's `1.5rem`
- [x] T008 [P] [US1] In `frontend/src/components/SettingsForm.vue` remove the form's own `max-width: 28rem` so it fills the right column, and make the controls fill the field width (`width: 100%`, `box-sizing: border-box` on inputs and the select, apart from the range slider's row)
- [x] T009 [P] [US1] In `frontend/src/components/FilePicker.vue` make a long file name wrap inside the column (`overflow-wrap: anywhere` on the name line) so it does not widen the left column or overlap the settings
- [x] T010 [US1] Verify Story 1 in the browser at about 1280 px using `quickstart.md` section 3 "Story 1" (including the failed-upload error appearing in the left column), and that at 1280 px the chooser, preview and "Create frames" are visible together without scrolling (SC-001); fix any layout issue found

**Checkpoint**: The two-column page is usable end to end.

---

## Phase 4: User Story 2 - Frame rate, window size and spacing share a row (Priority: P2)

**Goal**: One wrapping row for window size, frame rate and window spacing (FR-005).

**Independent Test**: Quickstart "Story 2". The three fields sit side by side, each with its own label and message; the spacing default and below-minimum notice still work.

- [x] T011 [US2] In `frontend/src/components/SettingsForm.vue` wrap the window size, frame rate and window spacing fields in one container laid out as a grid with `grid-template-columns: repeat(auto-fit, minmax(8.5rem, 1fr))` and a `0.75rem` gap, each field with `min-width: 0` so labels and messages wrap inside their own cell. Keep each field's label, control, validation error and (for spacing) the below-minimum notice with that field; do not change any wording
- [x] T012 [US2] Verify Story 2 in the browser using `quickstart.md` section 3 "Story 2": invalid frame rate error stays under its own field without breaking the row, the spacing default still follows window size and frame rate, and the below-minimum notice is readable; fix any layout issue found

**Checkpoint**: Settings column is three field rows shorter.

---

## Phase 5: User Story 3 - Explanations move into info popovers (Priority: P2)

**Goal**: Replace each helper line with an info button and popover; keep errors and the below-minimum notice inline (FR-006 to FR-011, FR-015).

**Independent Test**: Quickstart "Story 3". No explanatory sentence under any field; each setting has an info button whose popover shows its explanation, closes on Escape or outside click, and stays on screen.

- [x] T013 [P] [US3] Create `frontend/src/utilities/popover.ts` exporting `popoverPosition(anchor, popover, viewport, margin = 8)` that returns `{ left, top }` in viewport coordinates, where `anchor` is `{ left, top, bottom }` of the button, `popover` is `{ width, height }`, and `viewport` is `{ width, height }`. Place it below the anchor aligned to the anchor's left edge; if it would pass the bottom edge and there is more room above, place it above (bottom of the popover at the anchor's top); then clamp left to `[margin, viewport.width - popover.width - margin]` and top to `[margin, viewport.height - popover.height - margin]`, and when the popover is larger than the viewport use `margin`. Add `frontend/src/utilities/popover.test.ts` covering: default below and left-aligned; flipped above near the bottom; clamped at the left, right, top and bottom edges; a popover wider and taller than the viewport; no flip when there is more room below than above
- [x] T014 [P] [US3] Create `frontend/src/utilities/help.ts` exporting the explanation text for each setting, moved verbatim from `SettingsForm.vue`: `windowSizeHelp` ("Larger windows separate low notes better but blur changes over time."), `frameRateHelp` (`${FRAME_RATE_RANGE.min} to ${FRAME_RATE_RANGE.max}.`), `brightnessHelp` ("Whole number, 2 to 100. Higher values lift quiet notes more but show less contrast." built from `BRIGHTNESS_RANGE`), `smoothingHelp` ("0 is no smoothing; higher values fade notes more slowly."), and `spacingHelp(stepHint: string)` returning "Distance between the starts of windows, as a multiple of the window size." followed by a space and the step hint when the hint is not empty. Add `frontend/src/utilities/help.test.ts` checking each text, that the range texts follow the range constants, and `spacingHelp` with and without a step hint
- [x] T015 [US3] Create `frontend/src/components/InfoPopover.vue`. Props: `label: string` (the setting's name), `text: string`. Render a `<button type="button">` showing "i" with `aria-label="About {label}"`, `popovertarget` set to a unique id from Vue's `useId()`, and a `<div popover="auto" role="note" :id>` holding `text`. On the popover's `toggle` event when `newState === "open"`, measure the button (`getBoundingClientRect`) and the popover (`offsetWidth`/`offsetHeight`), call `popoverPosition` with the viewport's `clientWidth`/`innerHeight`, and set `left` and `top` in pixels. Close an open popover on window `resize` (remove the listener on unmount). The button must stay enabled while a job runs. If `vue-tsc` rejects the `popovertarget` attribute, bind it with `v-bind="{ popovertarget: id }"`
- [x] T016 [US3] Style `InfoPopover.vue`: a small circular button (about 1.25rem, visible focus ring); the popover with `position: fixed; inset: auto; margin: 0` (overriding the browser default that centers it), `max-width: min(18rem, calc(100vw - 1rem))`, padding, border, background, shadow and the page's font and `color`; text that wraps
- [x] T017 [US3] In `frontend/src/components/SettingsForm.vue` restructure each of window size, frame rate, window spacing, brightness and smoothing as a field container with a head row holding the `<label for>` text and the `<InfoPopover>` (outside the `<label>`, so activating the button does not focus the control), then the control, then only the inline messages: delete every explanatory `<small>` and keep the validation errors and the below-minimum spacing notice under their field. Give each control an `id`. Pass the `label` and the matching `help.ts` text to each `InfoPopover` (`spacingHelp(stepHint)` for spacing, using the existing `stepHint` computed). Keep the slider's `output` value and `aria` behavior
- [x] T018 [US3] Verify Story 3 in the browser using `quickstart.md` section 3 "Story 3": no helper line under any field, popovers open and close (button, Escape, outside click), only one open at a time, keyboard-only use, the button's accessible name and expanded state, the spacing popover with a valid and an invalid value, errors still inline, popovers working while a job runs, and popovers staying fully on screen near the window's right edge and at a narrow width

**Checkpoint**: All explanations are reachable on request and nothing printed under the fields but problems.

---

## Phase 6: User Story 4 - Narrow windows fall back to one column (Priority: P3)

**Goal**: Stacked layout with no sideways scrolling on phone-width windows (FR-012).

**Independent Test**: Quickstart "Story 4" at 360 px.

- [x] T019 [US4] Check the page at 360 px wide in the browser using `quickstart.md` section 3 "Story 4": the left column's content comes first and the settings after, the row of three wraps, no horizontal scrollbar appears (check the file name line, summary list, preview, slider and popovers), and popovers stay on screen. Fix any overflow found in `frontend/src/App.vue`, `frontend/src/components/SettingsForm.vue`, `frontend/src/components/FilePicker.vue` or `frontend/src/components/InfoPopover.vue` (typically a missing `min-width: 0` or a fixed width)

---

## Phase 7: Polish & Cross-Cutting Concerns

- [x] T020 [P] Update the "Audio frames UI" description in `README.md`: the page has a left column (chooser, progress and error messages, result summary, preview and playback) and a right column (settings and "Create frames"), window size, frame rate and spacing share a row, each setting's explanation is behind an info button that opens a popover, and the columns stack below 960 px. Remove or reword any sentence that says the helper text is printed under the fields
- [x] T021 Check SC-005 per `quickstart.md` section 4: temporarily add several dummy fields to `SettingsForm.vue`, confirm the preview's position and size do not change, then remove them
- [x] T022 Check SC-008 per `quickstart.md` section 5: with the same file and settings on this branch and on `main`, the request, frame count, summary text and sample frames are identical
- [x] T023 Run the full checks one last time: `npm test`, `npm run typecheck` and `npm run build` in `frontend/`, and `pytest` in `backend/`; confirm the counts are the baseline from T001 plus the new popover and help tests, and that nothing else changed

---

## Dependencies & Execution Order

- Phase 1 → Phase 2 (T002 and T003 in parallel, then T004, then T005) → stories.
- **US1** (T006–T010) needs Phase 2. T008 and T009 can run in parallel after T006.
- **US2** (T011–T012) needs Phase 2 only; it edits `SettingsForm.vue`, so do it after T008 if working on one branch.
- **US3**: T013 and T014 are independent of everything else and can start any time (even during Phase 2). T015 needs T013; T016 needs T015; T017 needs T014, T015 and Phase 2 and should follow T011 (same file); T018 last.
- **US4** (T019) needs US1 and is best done after US2 and US3 so it checks the final page.
- Polish after the stories; T020 can be done in parallel with any verification task.

## Parallel Example

```
T002 FilePicker.vue   |  T003 SettingsForm.vue   |  T013 popover.ts + test  |  T014 help.ts + test
```

## Implementation Strategy

1. **MVP**: Phases 1, 2 and 3 (US1). The two-column page works with the existing helper lines still printed; it already gives the preview its own column.
2. **Increment**: US2 (one row), then US3 (popovers), each checked in the browser by its quickstart steps.
3. **Finish**: US4 check at 360 px, README, SC-005 and SC-008 checks, full test run.

---

## Implementation Notes

- **Baseline and final counts**: frontend 127 tests before, 140 after (13 new: 9 for popover placement, 4 for the explanation text); backend 425 before and after. `typecheck` and `build` clean.
- **Browser checks** (T005, T010, T012, T018, T019, T021, T022) were run against the dev server in headless Chrome driven over the DevTools protocol, not by hand: layout at 1280, 980, 940 and 360 px, popover open/close by mouse, Enter, Space, Escape and outside click, only one open at a time, accessible names and expanded state, popovers inside the window at 420 px and at the right edge of 1280 px, controls disabled while busy with the info buttons still working, errors and the below-minimum notice inline, and the default spacing still following the window size.
- **Changes from the plan found while checking**: the right column is 30 rem (not 26) and the row cells are at least 8.5 rem (not 9), because three fields did not fit one row at 26 rem; the columns stack below 60 rem (960 px, not 768), because at 768 px the left column was only about 270 px wide; within the result, the preview and playback controls now come first and the file name heading, summary and notice follow, so the preview is directly under the chooser; the popover has `width: max-content` so its size does not depend on where it sits (it was squeezed to about 50 px near the right edge).
- **SC-003**: with the same five settings and no file chosen, the settings column is 271 px tall against 468 px for the old form (not counting the chooser), 42% shorter. **SC-005**: adding six more fields left the preview's position and size unchanged (settings grew from 271 to 505 px). **SC-008**: against a copy of `main`, the request fields, the result summary and a frame PNG (200, 959 bytes) were identical.
- The helper folder was first `frontend/src/lib/`, which the `lib/` rule in `.gitignore` (line 17) hides from git, so no file in it (new or from earlier features) was tracked. It was renamed to `frontend/src/utilities/` after implementation, which git sees.
