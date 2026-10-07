# UI Contract: Two-Column Layout and Info Popovers

The page is the only interface this feature changes. The server API and the job request/response are not touched.

## Page regions

At 60 rem (960 px) and wider, the page shows two columns:

| Column | Top to bottom |
|--------|---------------|
| Left | Audio file chooser (with prompt "Choose a .wav file.", or the file's name and size, and any file error) → progress message while a job runs → error message if the job failed → result: frame preview, playback controls, frame slider, then the file name heading, summary list and spacing-raised notice |
| Right | Row of three (window size, frame rate, window spacing) → brightness → smoothing → "Create frames" |

Below 960 px the columns stack in the same order (left content, then settings). No horizontal scrolling at 360 px.

Nothing from the result appears in the right column, and no setting appears in the left.

## Components

| Component | Props | Events | Notes |
|-----------|-------|--------|-------|
| `FilePicker` | `busy: boolean`, `file: File \| null` | `update:file(file \| null)`, `update:sampleRate(hz)` | Shows the file prompt/name/size and the file error (from `validateFile`). Disabled while busy. |
| `SettingsForm` | `busy: boolean`, `file: File \| null`, `sampleRate: number` | `submit(file, settings)` | Same `submit` payload as the former `UploadForm` (`JobSettings` unchanged). "Create frames" is disabled while the file or any setting is invalid, or while busy. |
| `InfoPopover` | `label: string` (the setting's name), `text: string` | none | Renders the info button and its popover. |

## Info button and popover behavior

- Each of window size, frame rate, window spacing, brightness and smoothing has one info button, placed beside its label (outside the `label` element).
- The button's accessible name is `About <label>` (for example "About window size"). It is operable with Enter and Space, mouse and touch.
- Activating it opens a popover beside the button showing the setting's explanation. The popover closes on Escape, on a click or tap outside it, and when the button is activated again. Opening one closes any other.
- Placement: below the button and aligned to its left edge; above it if there is not enough room below; always fully inside the viewport with a small margin.
- Info buttons stay usable while a job is running.
- No explanation sentence is printed under any field.

## Messages that stay visible

- Validation errors for every setting and for the file, under their field.
- The below-minimum spacing notice, under the spacing field.
- The job progress message, the job error message and the spacing-raised notice, in the left column.

## Unchanged behavior

Defaults, ranges and validation messages; the default-spacing recalculation when window size, frame rate or file changes; the submitted settings; the frames and playback; the result summary contents.
