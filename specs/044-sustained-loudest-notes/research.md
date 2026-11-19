# Research: Sustained loudest notes

No `NEEDS CLARIFICATION` remained in the Technical Context. The decisions below settle how the spec is built on the code as it is today (read on 2026-11-18).

## 1. One shared selection function, with the old behaviour at k = 0

- **Decision**: `held_notes.hold_loudest(values, count, extra=0) -> LoudestIndices`, a `(frames, count)` `intp` array: for each frame the index of the note (or letter) at each of the `count` places,
  loudest first. The six pictures replace `np.argsort(-shown, axis=1, kind="stable")[:, :count]` by it and keep the code after it unchanged (`take_along_axis(...) > 0`, `put_along_axis`, `% LETTERS`).
- **Rationale**: the current line is the same in `decay.gains`, `chromatic_decay._raw_gains`, `polar_chords._targets` and `polychord.loudest_letters` (`decay_exp` reaches it through `decay.gains`). With
  `extra = 0` the rule below gives exactly the old array (shown in decision 3), so `extra=0` is a default that changes nothing for any caller and any existing test, and lets
  `verify_drawing.py` prove it.
- **Alternatives considered**: (a) a selection as a boolean mask `(frames, notes)`: the callers need the loudness order (the gains 24, 20, 16, 12, 8 and the bar volumes go by it), so an order is what they use;
  (b) a separate function in each module: four copies of a stateful rule would drift.

## 2. The algorithm

For each frame `f`, with `n = count` and `k = extra`:

1. `order[f]` = stable argsort of `-values[f]` (equal strengths: the lower index first) and `rank[f, note]` its inverse (rank 0 is the loudest). Both are made for all frames at once with NumPy.
2. `kept` = the notes of the previous selection (`selected[f-1]`) whose `rank[f, note] < n + k` **and** `values[f, note] > 0`.
3. `free = n - len(kept)`. The newcomers are the first `free` notes of `order[f]` that are not in `kept` and have `values > 0` (a scan of at most `n + free` entries, because at most `n` of the
   first entries are held; it stops at the first value that is not above 0, as every later one is also 0).
4. `selected[f]` = `kept + newcomers`, sorted by `rank[f, ·]` (so by loudness, ties to the lower note).
5. The returned row is `selected[f]` padded to `count` with notes whose value is 0 (the first not-selected entries of `order[f]`, which are all 0 when fewer than `count` notes sound), so a caller's
   `values[order] > 0` test still says "this place is empty".

Frame 0, and any frame after a frame with no sound, starts from an empty previous selection (`kept` empty), so it is the plain n loudest (spec FR-001). The loop over frames is the only Python loop;
every step in it is a few operations on at most `n + k <= 16` numbers, about 10 microseconds, so 30,000 frames take well under a second.

**Why a newcomer is always in the loudest n**: a free place exists only when fewer than `n` held notes remain, all of them within the loudest `n + k`; the best note that is not held therefore has rank
at most `n` (counting from 1), because the held notes occupy at most `n - 1` of the ranks above it. So FR-003 ("a newcomer takes a free place only") needs no extra test in the code, and the spec's
"loudest note that is not held" is also "within the loudest n".

## 3. k = 0 is the old behaviour (so `extra=0` is a safe library default)

With `k = 0` a held note stays only while `rank < n`, i.e. while it is among the loudest n; every place left free is given to the best notes that are not held, in order. The selection is then the set of
the loudest n, sorted by rank: the old array, element for element. This is proved by a test that compares `hold_loudest(v, n, 0)` with the old expression on random and tied data, with zeros and with fewer
than `n` notes sounding. The user's range for the setting starts at 1 (the spec), so the page and the request refuse 0; the library accepts it as "off".

## 4. Where the selection is applied

| Picture | Function that changes | Unit | n |
|---|---|---|---|
| Decay | `decay.gains` (and `circle_points`) | note (84) | 5 (`len(GAINS)`) |
| Decay Exp | `decay_exp.exp_gains`, `circle_points` pass `extra` to `decay.gains` | note | 5 |
| Chromatic Decay, Chromatic Wireframe | `chromatic_decay._raw_gains`, `letter_gains`, `circle_points` (the wireframe draws these points) | letter (12, from `letter_energies`) | 5 |
| Polar Chords | `polar_chords._targets`, `note_targets`, `polar_bars` | note (84) | 5 to 8 (`count`) |
| Polychord | `polychord.loudest_letters`, `write_polychord_frames` | note (84), then its letter | 5 to 8 (`settings.notes`) |

`frame_rendering.write_frames` gets `extra_notes: int = 0`, checks it with `check_extra_notes(extra_notes, n)` for the six types (n from the type: 5, or `polar_notes`, or the Polychord notes), and passes it
to the picture. For the other three types it is checked as a whole number from 0 to 8 and ignored, like the other settings that do not apply (`decay_amounts`, `wave_count`, ...).
The chord bar of Polar Chords (`chords.measure_chords`, from the analysis windows) is not touched (spec Assumptions).

**The threshold of Chromatic Decay / Wireframe** is applied first (`apply_threshold` in `circle_points`), so the letters' energies already have the faint notes at 0 when the selection is made; no
change to that order.

## 5. The request and the answer

- **Decision**: a new form field `extra_notes` (text), parsed by `_parse_extra_notes(text, sent)`: not sent means `DEFAULT_EXTRA_NOTES` (2); sent must be a whole number from 1 to 8 (`MAX_EXTRA_NOTES`),
  else 400 "The extra notes must be a whole number from 1 to 8." before the file is read. After the image type and the settings that give n are known (`polar_notes`, `polychord_notes`), for the six
  types `extra_notes <= n` is checked, else 400 "The extra notes must be a whole number from 1 to {n}." (also before the file is read). The answer gains the key `extra_notes`. See
  [contracts/job-api.md](contracts/job-api.md).
- **Rationale**: the spec's FR-011 (refused before the file is read, names the range, ignored by the other pictures, echoed). The 1 to 8 range for pictures without an n is the widest valid value,
  so "accepted and ignored" holds for every value the page can send; a value that is not a whole number from 1 to 8 is refused for every picture, as `threshold` and the others are.
- **Alternatives considered**: refusing only when it exceeds n and silently ignoring junk for the other types: inconsistent with the other settings, whose bad values are refused for every type.

## 6. The page

- **Decision**: a new group `held-notes` (title *Held notes*) with one control `extra-notes` (label *Extra notes (k)*), shown for Decay, Decay Exp, Polar Chords, Chromatic Decay, Chromatic Wireframe and
  Polychord (`usesHeldNotes(imageType)`), placed after the group of the type and before Note layout / Local peaks. The control is a slider from 1 to n (a `max` that follows the picture's n: 5, or the
  Notes shown / Number of notes value), step 1, default 2. A value above the current n (the user lowered the notes after setting k) shows the error under the control and nothing is sent, as the other
  controls do. The result list shows *Extra notes (k)* for the six types.
- **Rationale**: the groups already put each picture's settings together and show only what applies; a group of its own is one place for a setting that six pictures share (a control in each of the six type
  groups would be six copies). The slider matches Notes shown and Number of notes.
- **Alternatives considered**: a number field (no live n limit): the slider's `max` shows the limit; a control in each type group: six copies of one setting.

## 7. Documentation (constitution II and III)

- A new alias `LoudestIndices` in `array_types.py` (`Shape: (frames, count)`, *Meaning*, *Made by: `held_notes.hold_loudest`*).
- `held_notes.py` has its `Order of operations:`; the lists of `decay`, `decay_exp`, `chromatic_decay`, `polar_chords`, `polychord`, `frame_rendering`, `jobs` get the new step or the new argument; the
  overview of `image_types.py` adds the held-notes step to the stages of the six pictures; `test_documentation.py` lists the new module.
- The help text of the setting and the descriptions of the six pictures in `imageTypeHelp` say "held". The README gets one bullet (as feature 043 did).

## 8. Tests

- `test_held_notes.py`: the rule against `specs/044-sustained-loudest-notes/tools/reference_selection.py` (an independent plain-Python version written from the spec, not from the code) on random data for
  every k from 0 to n and several n; `extra=0` equals the old expression; the scenarios of the spec's acceptance lists by name (User Stories 1 and 2, the ties, the exact rank n + k, the silent frame, fewer
  than n notes, a note that returns).
- One test file per picture group for "the held note is still drawn" (User Story 4) using the library functions, plus API tests for the request (User Story 3).
- The existing tests that compare a job's frames with the library output from the spied `write_frames` kwargs (`test_polychord_api`, `test_chromatic_wireframe_api`, `test_frame_rendering_polychord`)
  gain the extra argument.

## 9. Why `verify_frames.py` is not the no-change gate

`verify_frames.py` goes through the job, whose default k is 2, so any file with a displaced note differs by design. The no-change gate is `verify_drawing.py`, which draws from fixed note values with the
library defaults (`extra = 0`): it must report 0 differences. A third check is new in this feature: `verify_drawing.py` is run with `--extra 2` into a different baseline file only if a reviewer wants to
see the change (not a gate).

## 10. Risks

- A test that builds expected pictures from the library with the arguments the job gave `write_frames` fails until `extra_notes` is passed there too; they are found by running the suite.
- Jobs made by tests with pulses or fading tones may now differ from a hard-coded expectation where a note is displaced; each such test is read and fixed, or its premise (a steady tone) is restored.
- The known 32 baseline failures are in the same files; the comparison is by test id.
