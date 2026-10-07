# Data Model: Two-Column UI

No stored or transmitted data changes. The request to the server, the job result and the frames are as before. This describes the page-level state and the shape of a setting after the split.

## Page state (owned by `App`)

| Field | Type | Notes |
|-------|------|-------|
| `file` | `File \| null` | The chosen audio file. Set by `FilePicker`; read by `SettingsForm` for validation and submission. |
| `fileSampleRate` | number (Hz) | The chosen file's sample rate; 44 100 until a file is chosen or when the header cannot be read. A stale read (the user chose another file meanwhile) is ignored, as today. |
| `status` | `"idle" \| "busy" \| "done" \| "error"` | Unchanged. Drives the progress and error messages in the left column and disables the chooser and settings while busy. |
| `result` | `JobResult \| null` | Unchanged. Drives the summary and preview in the left column. |
| `errorMessage` | string | Unchanged. |

## Setting (owned by `SettingsForm`)

| Setting | Value | Inline (always visible) | Explanation (in popover) |
|---------|-------|--------------------------|--------------------------|
| Window size (samples) | one of `WINDOW_SIZES`, default `DEFAULT_WINDOW_SIZE` | validation error | "Larger windows separate low notes better but blur changes over time." |
| Frame rate (frames per second) | text → number, default 30 | validation error | the `FRAME_RATE_RANGE` line ("1 to 60.") |
| Window spacing (× window size) | text → number, defaults from sample rate, frame rate and window size | validation error, or the below-minimum notice | a short static sentence plus the step hint ("Step between windows: N samples (M ms).") when the value is valid |
| Brightness | text → whole number in `BRIGHTNESS_RANGE` | validation error | the range and the "higher values lift quiet notes more" sentence |
| Smoothing | number in `SMOOTHING_RANGE`, slider | validation error | "0 is no smoothing; higher values fade notes more slowly." |

Validation rules, defaults, ranges, the default-spacing recalculation and the submitted settings are unchanged (`JobSettings` is identical).

## Explanation

A plain string per setting, produced by `help.ts` from the setting's current state. Only the spacing explanation depends on state (the step hint); the others are constant.

## Popover state

Held by the browser (the native popover's open/closed state), not by the application. At most one popover is open at a time. Position is computed on open from the button's and popover's rectangles and the viewport size (`popoverPosition`), and is not stored.

## Layout regions

| Region | Contents |
|--------|----------|
| Left column | `FilePicker`; busy and error messages; the result: `FramePlayer` (preview, controls, slider), then heading, summary, spacing-raised notice |
| Right column | `SettingsForm`: the row of three, brightness, smoothing, "Create frames" |
| Narrow window | One column: left-column content first, then the settings |
