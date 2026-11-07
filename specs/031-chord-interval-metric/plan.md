# Implementation Plan: Chord Interval Metric

**Branch**: `031-chord-interval-metric` (no git branch created; spec directory name only) | **Date**: 2026-11-06 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/031-chord-interval-metric/spec.md`

## Summary

A new **measurement**, built on the 84 note strengths of every analysis window, that records **which of the requested chord types the loudest letters form, and in which inversion** (revised 2026-11-07: the notes are combined into the 12 letters, and a type looks at more letters than it has notes). Measurement only, like Local Peaks (feature 023): no job field, no response key, no page control, no picture changes (FR-011); the code to record the data, to be used by a later feature.

A chord type is a tuple of 1 to 3 steps above an implied root (`(4, 7)` = notes 0, 4, 7). The 84 notes of a window become 12 letters (octaves added up; a letter stands for its loudest octave; a letter under a millionth of the loudest is silent). For a type with `n` intervals the measurement takes the `n + 3` loudest letters (4, 5 or 6; ties to the lower letter), tries every choice of `n + 1` of them, folds the notes of the choice down by octaves to less than an octave above the lowest, and compares the steps with every inversion of the type. Of all matches, one is recorded: most intervals, then the loudest letters, then the largest interval, then the lowest inversion, then the first choice of the louder letters. A record holds the type, the inversion and the original notes; a window with no match records "no chord". Optionally the measurement uses the picture's own limits: a **number of notes** (feature 017) and a **threshold** (feature 011), so that only notes the picture would use take part.

How it is done (research Decisions 1 to 6):

- **One new module, `chords.py`, with no knowledge of audio, frames or the router.** It takes an array of note strengths `(windows, 84 or more)` and the chord types, and returns a `ChordSeries`. Pure numpy; no new dependency.
- **The result is stored like the bins**: three small arrays with one entry per window (the index of the chord type, the inversion, the original notes padded to 4), `-1` for "no chord", plus the tuple of chord types. `record(i)` gives a readable `ChordRecord`. One entry per window, in window order, nothing depends on neighbours.
- **Matching is done on a 12-bit mask.** The folded steps of a window become a bit mask of which steps above the lowest note sound; every inversion of a chord type is a precomputed mask. A window's choice of letters matches an inversion when the masks are equal (different letters always give `n + 1` bits). The whole file is matched with array operations, with a loop over the choices of letters (6, 10 or 15 for a type) and not over windows.
- **Selection is a score of five kinds** per (window, type, choice): `(n, loudness of the letters, widest interval, −inversion, −index of the choice)`, compared one after the other (`_greater`), so the greatest is the winner in the order of the spec's rules; only a greater score replaces the one found. (Two different chord types never tie on all five, so the list order does not decide anything in practice.) The loudness comes before the widest interval, a deliberate change to the order of the user's rules, so that a faint note cannot win by making a wide interval (research Decision 4).
- **The picture's limits are reused, not copied.** The number of notes uses `note_selection.top_energy_notes` on the first 84 columns; the threshold uses `frame_rendering.hidden_below` (imported when needed, so that the picture module can use chords later without a cycle), with the largest value of the whole array as the peak, as the picture does. The messages and ranges are therefore the pictures' own. Chosen notes keep their real pitch (they are not spread over the grid).
- **Parameters are checked first** with messages that name the problem (no types, wrong number or kind of intervals, order, duplicates), before any measuring.
- **Tests**: inversion patterns, the folding, every worked example of the spec, the selection rules against an independent brute-force oracle, an exhaustive check of every chord type and inversion in several octave placements, the note limits against the picture's own functions, the stored arrays, determinism, the refusals, and one end-to-end test through the real note analysis with synthesized chords. The existing suites prove nothing else changed.
- **Docs**: README paragraph; `quickstart.md`.

## Technical Context

**Language/Version**: Python 3.10 (backend `.venv`). No frontend change.

**Primary Dependencies**: Existing only: numpy. No new dependency.

**Storage**: None (an in-memory result, like `LocalPeaks`).

**Testing**: pytest (`test_chords.py`; `test_chords_audio.py` for the end-to-end case with the real note analysis).

**Target Platform**: Local developer machine.

**Project Type**: Web application, existing `backend/` project; this feature touches the backend library only.

**Performance Goals**: A 60 second file at the default analysis spacing with 10 chord types takes no more than a few seconds beyond the analysis (SC-007). Vectorised over windows: a few array operations per chord type.

**Constraints**: Deterministic; the job request, response, settings page, pictures and frames unchanged (the existing reference-hash tests still pass); no loudness threshold or note limit of its own.

**Scale/Scope**: One new module (about 200 lines), its tests, the README. Nothing else is edited.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` is still the unfilled template, with no ratified principles, so no gates apply. Result: **PASS (no constraints defined)**. No new dependency. Re-check after Phase 1: **PASS**.

## Project Structure

### Documentation (this feature)

```text
specs/031-chord-interval-metric/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── chords.md
├── checklists/
│   └── requirements.md
└── tasks.md             # /speckit-tasks (not created by /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── app/services/
│   └── chords.py              # NEW: check_chord_types, inversion_patterns, measure_chords, ChordRecord, ChordSeries
└── tests/
    ├── test_chords.py          # NEW: the rules, the examples, the oracle, the exhaustive check, the limits, the arrays
    └── test_chords_audio.py    # NEW: synthesized chords through the real note analysis
README.md                      # a paragraph
```

**Structure Decision**: Existing web-application layout. `chords.py` sits beside `local_peaks.py` and `note_selection.py` in `app/services/` and, like them, knows nothing about the router, the frames or the pictures.

## Complexity Tracking

> No Constitution Check violations to justify.
