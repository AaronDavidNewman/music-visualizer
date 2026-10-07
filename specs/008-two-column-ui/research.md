# Research: Two-Column UI

No `NEEDS CLARIFICATION` items remained in the spec. These are the design decisions the plan rests on.

## Decision 1: Native Popover API for the info popovers

- **Decision**: The info button uses `popovertarget` and the popover element uses the `popover` attribute (automatic mode).
- **Rationale**: Automatic popovers already do what FR-008 asks: they close on Escape and on a click outside, and opening one closes any other automatic popover. They also render in the top layer, so no ancestor can clip them, and the browser exposes the button's expanded state to assistive technology. This removes the open/close, outside-click and focus code we would otherwise write and test.
- **Alternatives considered**: (a) A hand-built popover (a `div` toggled by state, document-level click and key listeners). More code, the clipping and stacking problems are ours to solve, and there is no DOM test environment to prove it. (b) A UI library. A new dependency for one widget. (c) The `title` attribute or a CSS hover tooltip. Not usable on touch or by keyboard, so it fails FR-007 and FR-010.

## Decision 2: Position with a small script, not CSS anchor positioning

- **Decision**: On the popover's `toggle` event, compute its position from the button's bounding box with a pure function (`popoverPosition`) and apply it as `left`/`top`. The default is below the button and left-aligned with it. It flips above if there is no room below, and is clamped horizontally and vertically so it stays within the viewport.
- **Rationale**: CSS anchor positioning would do this declaratively, but browser support is not yet universal, and FR-011 (stay inside the window, including narrow widths) must hold everywhere. A pure function is also the one part of this feature that can be unit-tested without a DOM.
- **Alternatives considered**: Anchor positioning with `position-try` fallbacks (not dependable across the target browsers yet). Leaving the popover at the browser default, which is the center of the window and detached from its button (fails "next to the button").

## Decision 3: Split `UploadForm` into `FilePicker` and `SettingsForm`; lift the file to `App`

- **Decision**: `FilePicker` emits the chosen file and the sample rate read from its header. `App` stores both and passes them to `SettingsForm`, which still emits `submit(file, settings)`.
- **Rationale**: The chooser must sit at the top of the left column and the settings in the right, so they cannot stay one component with one root. The spacing default depends on the file's sample rate and `canSubmit` depends on the file, so the file is shared state and belongs to the common parent. Keeping the `submit` signature leaves `App.onSubmit`, `submitJob` and the request untouched (FR-014).
- **Alternatives considered**: (a) One component using `Teleport` or slots to place the chooser elsewhere. It hides the real structure and is harder to read. (b) A native `form` attribute linking a chooser outside the form. It works for submission but not for the shared sample-rate state. (c) A store or composable. More machinery than one lifted ref pair needs.

## Decision 4: Single wrapping row for the three settings

- **Decision**: Window size, frame rate and spacing sit in one grid row (`repeat(auto-fit, minmax(8.5rem, 1fr))`), each field keeping its label, control and inline message. At narrow widths the row wraps onto more lines by itself.
- **Rationale**: Satisfies FR-005 at desktop width and the wrap requirement of Story 4 with no breakpoint code. Messages sit under their own field and wrap within its width, so a long message does not break the row.
- **Alternatives considered**: A fixed three-column grid, which cannot wrap at 360 px. Flexbox with fixed widths, which is brittle as labels change.

## Decision 5: What counts as "explanation"

- **Decision**: Moved into popovers: the window size, frame rate, brightness and smoothing helper lines (including the numeric ranges), and the step-between-windows hint under spacing. Kept inline: validation errors, the below-minimum spacing notice, and the file chooser's prompt and file name/size.
- **Rationale**: The spec's assumption: things the user must act on or that confirm their input stay visible; text that teaches what a setting does moves. The spacing field had only a computed hint and no static sentence, so its popover carries one short static sentence ("Distance between the starts of windows, as a multiple of the window size.") followed by the live step hint. This is the one new wording, needed so the popover is not empty while the value is invalid.
- **Alternatives considered**: Keep the step hint inline, because it is live feedback. Rejected: it is the line that makes the spacing field tall, and the spec classes it as explanation. Keep ranges inline. Rejected: the validation error already states the range when it matters.

## Decision 6: Breakpoint and column widths

- **Decision**: Two columns at 60 rem (960 px) and wider, stacked below. The right column has a fixed width of 30 rem (three fields of at least 8.5 rem fit on one row) and the left column takes the rest, so the preview can reach its existing 660 px maximum. The page's maximum width grows from 48 rem to about 76 rem.
- **Rationale**: At 1280 px this leaves room for the 660 px preview beside the settings. The break was first 768 px, but there the left column was only about 270 px wide and squeezed the preview, so it moved to 960 px (left column about 420 px at the break). The spec leaves the exact value to design.
- **Alternatives considered**: Equal 50/50 columns, which waste space on the form and squeeze the preview. A `container` query on each column. Unneeded for one break.

## Decision 7: How the behavior is verified

- **Decision**: Unit-test the pure helpers (placement/clamping, explanation text) with vitest. Check layout, popover open/close, keyboard use and stacking in a real browser by the quickstart steps, and keep `typecheck`/`build` clean.
- **Rationale**: The frontend test setup has no DOM environment. Adding jsdom and a component-test library would be a new dependency and jsdom does not implement the Popover API or layout, so it would not verify what matters here.
- **Alternatives considered**: jsdom plus Vue Test Utils (new dependencies, does not cover layout or popover behavior). Playwright (heavier than this change warrants, and not currently in the project).

## Decision 8: Accessibility details

- **Decision**: Each info button is a real `button` with `aria-label="About <setting>"` and the popover has `role="note"`, its text being plain content. Buttons are not part of the disabled controls while a job runs (FR-015), and sit outside the `label` they accompany so that activating one does not focus the field.
- **Rationale**: The native invoker relationship exposes expanded/collapsed to screen readers, the label names the setting (FR-010), and keeping the button outside the `label` stops a click from also activating the control.
- **Alternatives considered**: Putting the button inside the label (a click would then be forwarded to the input). Using `aria-live` to announce the text on open (noisy when the content is reachable right after the button).
