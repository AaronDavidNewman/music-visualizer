# Research: Note Smoothing

No `NEEDS CLARIFICATION` items are open. These are the design decisions.

## Decision 1: The recurrence

- **Decision**: For frame rows `x[0..F-1]` of 88 note values, the output is `y[0] = x[0]` and `y[n] = s × y[n-1] + (1 − s) × x[n]` for `n ≥ 1`, with each of the 88 columns independent. Implemented as a loop over frames, each step one vector operation over the 88 notes.
- **Rationale**: This is the spec's reading of the request (a running average using the previous *smoothed* value, first frame skipped). With s = 0.5 and values 0, 10, 0, 0 it gives 0, 5, 2.5, 1.25. A loop mirrors the formula exactly, so a reader can check it against the spec, and at 30,000 frames it costs a few tens of milliseconds.
- **Alternatives considered**: `scipy.signal.lfilter` with a start state (same result, less obvious, and needs care to keep the first frame unchanged); the unsmoothed previous value (the spec records this other reading and chose against it).

## Decision 2: Exact identity at 0

- **Decision**: When `smoothing == 0`, `smooth_frames` returns a copy of the input without doing the recurrence.
- **Rationale**: SC-001 asks for pixel-for-pixel identical images. A copy removes any doubt about floating-point behavior at s = 0 and keeps the default path as cheap as before.
- **Alternatives considered**: Running the recurrence at 0 (it would be exact too, since `0 × y + 1 × x = x`, but the shortcut makes that obvious and avoids the loop).

## Decision 3: Where it sits in the pipeline

- **Decision**: Frame values are averaged (`average_frames`), then smoothed (`smooth_frames`), then handed to `write_frames`, which scales them to 0–255 against the largest value (now the largest smoothed value), brightens them and draws them.
- **Rationale**: FR-005 and the spec's assumption: smoothing acts on note values before scaling, so the scale follows the smoothed maximum and the loudest tile still reaches full white. Analysis, window spacing, frame count and timing are not touched (FR-012).
- **Alternatives considered**: Smoothing the gray levels after scaling (the maximum would stay at the unsmoothed peak, making smoothed pictures dimmer, and smoothing would act on a non-linear, rounded scale); scaling against the unsmoothed maximum (rejected in the spec).

## Decision 4: Validation, including the empty value

- **Decision**: The router reads `smoothing` as text. An omitted field means 0.0. A field that was sent, including an empty or blank one, must parse as a finite number from 0.0 to 0.8 inclusive, otherwise 400 `The smoothing must be a number from 0.0 to 0.8.` It reuses the existing `_sent_fields` dependency, which tells "not sent" from "sent empty" (FastAPI otherwise reports an empty form value as missing). The check runs with the other parameter checks, before the file is stored.
- **Rationale**: FR-006 and FR-007 and SC-007, same rule and same mechanism as brightness. `-0.0` is accepted and treated as 0. Any number of decimals is accepted within the range (the slider only produces two).
- **Alternatives considered**: Treating an empty value as the default (the spec says to refuse it); rounding to two decimals on the server (silently changes what a script asked for).

## Decision 5: Reporting the value

- **Decision**: The response adds `smoothing` as a number, the value used (0.0 when none was sent).
- **Rationale**: FR-011. The summary can show it, and scripts can confirm what ran.
- **Alternatives considered**: None needed.

## Decision 6: The slider

- **Decision**: A native range input with `min = 0`, `max = 0.8`, `step = 0.01`, starting at 0, with a number readout showing the value to two decimals (`toFixed(2)`). The value is rounded to two decimals (`Math.round(v × 100) / 100`) before it is sent. It is disabled while busy and keeps its position after errors and successes like the other fields.
- **Rationale**: FR-008 to FR-010. With the range 0 to 0.8 in steps of 0.01 the slider has 81 positions and the right end is exactly 0.8. Rounding on the client prevents float noise such as 0.30000000000000004 in the request and the summary.
- **Alternatives considered**: A slider with a free-typing number box (more UI, no requirement); steps of 0.05 (coarser than the spec's 0.01); a custom slider component (the native input is accessible and keyboard-operable already).

## Decision 7: Validation helper on the client

- **Decision**: `lib/validation.ts` gains `SMOOTHING_RANGE = { min: 0, max: 0.8, step: 0.01 }`, `DEFAULT_SMOOTHING = 0`, `validateSmoothing(value)` (a finite number from 0 to 0.8, else the same message as the server) and `formatSmoothing(value)` (two decimals). The form uses the range constants for the slider and `validateSmoothing` as a guard in `canSubmit`.
- **Rationale**: One definition of the range, unit-tested, and the same message on both sides. The slider cannot produce an invalid value, but the guard keeps the form safe if the control is ever replaced.
- **Alternatives considered**: Hard-coding the numbers in the template (untestable and easy to change on one side only).

## Decision 8: The settings object

- **Decision**: `JobSettings` gets `smoothing: number` and `submitJob` sends it as `smoothing`; `JobResult` gets `smoothing: number`; the results summary adds "Smoothing: 0.30" using `formatSmoothing`.
- **Rationale**: Feature 004 already moved the form to one settings object, so this is one more field.
- **Alternatives considered**: None needed.

## Decision 9: Checking the effect on real data

- **Decision**: In addition to unit tests, the implementation measures on `fotr-intro1-echo.wav`: smoothing 0 against the previous output (identical), the fade lengths on a real note, and total time at 0 and 0.8 (SC-008). A picture of consecutive frames at 0 and 0.8 is produced and looked at.
- **Rationale**: Unit tests use made-up sequences; the real file shows that the visual effect is what the spec describes, and the timing check covers SC-008.
- **Alternatives considered**: Unit tests only (cannot show the visual result).
