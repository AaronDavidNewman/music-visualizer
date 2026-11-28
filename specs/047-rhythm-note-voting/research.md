# Research: Rhythm Circles Tempo Voting from Sustained Loudest Notes

Feature 047 (2026-11-25). Spec: [spec.md](spec.md). Nothing in the Technical Context was left as NEEDS CLARIFICATION; this file records the design decisions, with what was
read in the code first.

## What exists today (read before deciding)

- `rhythm_circles.py`: `CIRCLES = 4` (the tempo finder's current tempo, its rate of change, the local peak's rate, its rate of change), `DEFAULT_SPEEDS = (120, 0, 60, 0)`,
  `peak_series(times, tempos)` -> `CircleSeries (peaks, 4)`, `circle_speeds` and `circle_angles(times, series, moments)` (a step function with the breakpoints `times`, the angle
  the running total of `speed / 60`), `rhythm_angles(peaks, frame_rate, frames)` -> `RhythmData(angles (frames, 4))`, the rings (`ring_colors_rows` at `(k - 1) / 3`,
  `_geometry` ring width `outer / CIRCLES`).
- `jobs.py` measures the peaks once for Rhythm Circles (`measure_local_peaks(..., peak_distance, DEFAULT_PROMINENCE)`), calls `rhythm_angles` **before** `write_frames`, and
  passes the finished `RhythmData` in; `write_frames` only checks the frame count and draws.
- `held_notes.hold_loudest(values, count, extra)` -> `LoudestIndices (frames, count)` is what the other n-loudest pictures use; it fills the places of a frame with fewer than
  `count` sounding notes with notes whose strength is 0, so "sounding" must be read from the strengths, not from the indices.
- `average_frames(result, fps, frames)` in the job makes the `(frames, 88)` note strengths that every picture draws from; the notes are the first 84 columns.
- The frequency buffers are always 60 ms apart (`buffer_interval.BUFFER_INTERVAL_MS`), whatever the frame rate; a frame averages the buffers that start in it.

## Decision 1 - One new pure module, `tempo_votes.py`

**Decision**: everything that is a number is a pure numpy function in a new `backend/app/services/tempo_votes.py`, testable without audio:
`check_vote_limit`, `note_starts` (the starts from the note strengths), `fitting_tempos` (which of the 18 tempos fit each note length), `vote_tempos` (the votes after every
start), `ranked_tempos` (the first and second tempo after every start) and `vote_series` (the four circle series from them). `rhythm_circles.py` imports it; the drawing and the
two local-peak circles stay in `rhythm_circles.py`.

**Rationale**: the same split as `tempo_finder.py` (a pure rule) and `rhythm_circles.py` (the picture); the spec asks (FR-014) for tests with start times alone.

**Alternatives considered**: putting the voting inside `rhythm_circles.py` (rejected: that module is already about the picture and the series; the voting has its own constants,
setting and checks); extending `tempo_finder.py` (rejected: it is a different rule, and Polychord still uses it).

## Decision 2 - A start is a sounding note entering the held selection

**Decision**: `note_starts(values, extra, frame_rate)`: take `hold_loudest(values[:, :84], LOUDEST_COUNT (5), extra)`, mark the notes of each frame that are in the selection **and
sound** (`values > 0`), and a frame is a **start** when it has a sounding selected note that was **not** sounding-and-selected in the previous frame (every sounding note of the
first frame enters). Frames with several entering notes are one start. The time of a start is the middle of its frame, `(f + 0.5) / frame_rate`, the moment the beat and the
rhythm angles already use. A note that drops out (or the selection that goes silent) and comes back is a new start; a note that stays selected is not.

**Rationale**: it is the spec's definition (FR-001) and uses the sustained loudest notes of spec 044 as the user asked; strength 0 must be excluded because `hold_loudest` pads
the places. One start per frame is what gives "no length of 0".

**Alternatives considered**: detecting onsets from a rise in strength (rejected: not what was asked, and a held note's wiggles would count); using the notes of the 12 letters
(rejected: the user said notes); a larger n than 5 (rejected: no setting asked; 5 is what Decay, Chromatic Decay and Wireframe use).

## Decision 3 - The fit rule, vectorized, with a 1e-9 slack on the inclusive comparisons

**Decision**: the 18 tempos are `72 + 4n`, n = 1..18; the note values in beats are `NOTE_BEATS = (2, 1, 1/2, 1/4, 3, 3/2, 3/4, 3/8, 1/3, 2/3)`. For the lengths `L` of all cycles at
once, the array `fits (cycles, 18)` is true where, for some `b`, `abs(60 b / L - T) <= 2` **or** `abs(60 b / T - L) <= resolution / 2` (spec FR-006); the comparisons get a slack of
1e-9 so that the exact cases (0.5 s and the implied 90 against 88 and 92) are inclusive in floating point. The resolution is the larger of one frame (`1 / frame_rate`) and
the 60 ms of `BUFFER_INTERVAL_MS`, passed to the voting as a number (0 in the tests of exact start times).

**Verified by hand and by a script (2026-11-25)**: for L = 0.5 and resolution 0 the fitting tempos are exactly {80, 88, 92, 120}; with the 60 ms resolution L = 0.5 fits 8 tempos
and L = 0.25 fits 16 of the 18 (the figure the spec quotes).

**Rationale**: `(cycles, 18, 10)` is at most a few hundred thousand booleans for a long file, one numpy expression, no loop.

**Alternatives considered**: the half-bin test alone (rejected in the spec: a start known to a frame would almost never match); a length-only test (rejected: the half bin is the
user's statement of the binning, and it is the only test when the resolution is 0).

## Decision 4 - The votes: one short loop over the cycles

**Decision**: `vote_tempos(start_times, resolution, limit)` returns `TempoVotes (starts, 18)`, the votes after each start (row 0, the first start, is all 0). For each later start:
`votes = max(votes - 1, 0)`, then `votes[fit] = min(votes[fit] + 2, limit)`. The recursion is sequential (the clamps), so it is a Python loop over the cycles of 18-element
operations (a 5-minute file has well under 5,000 starts; measured to be milliseconds), the fit array being made first for all cycles.

**Rationale**: FR-004 exactly (subtract, then add, clamp); a vectorized form would have to handle the clamps and is not worth it.

**Alternatives considered**: `np.cumsum` with clipping tricks (rejected: the two clamps do not commute with a sum).

## Decision 5 - Ranking, and a place without votes holds 120

**Decision**: `ranked_tempos(votes)`: for every row, `np.argsort(-votes, axis=1, kind="stable")` over the tempos in ascending order, so a tie goes to the lower tempo (FR-008); the
first and second places are the first two columns; a place whose votes are 0 holds `START_TEMPO` (120, from `tempo_finder`, so one value of the starting tempo) instead of the
tempo it happened to be. Returns `RankedTempos (starts, 2)`.

**Rationale**: spec Edge Cases; with no votes at all, both places are 120 and the circles start exactly where the old tempo circle started.

## Decision 6 - The six series, and one `circle_angles` for two kinds of events

**Decision**: the vote circles change at the **starts**, the local peak circles at the **peaks**, so the series cannot share one breakpoint list. `circle_speeds` and
`circle_angles` get a `defaults` parameter (the speeds before the first event, a tuple) and take their width from it; the angles of the four vote circles come from
`circle_angles(start_times, vote_series, moments, VOTE_DEFAULTS)` and those of the two peak circles from `circle_angles(peak_times, peak_series, moments, PEAK_DEFAULTS)`, joined
side by side: `CircleAngles (frames, 6)`. `peak_series` now gives `(peaks, 2)` (the peak's rate and its change; the tempo finder is no longer called here). The rate of change of a
vote circle is `diff(level) / diff(start_times)` (0 for the first start), the convention of the peaks. `CIRCLES = 6`, the ring width `outer / 6`, the rings at `(k - 1) / 5`.

**Rationale**: the integral of a step function is exact per group; merging the event times of both would multiply the code and make the vote circles depend on peak positions.

**Alternatives considered**: merging the two event lists into one breakpoint list with forward-filled series (rejected: more code and no benefit); keeping `CircleSeries` at
`(events, 4)` and adding a second alias (the alias is kept and described for any width: `(events, circles)`).

## Decision 7 - The setting: `vote_limit`, a request field, a page group of its own

**Decision**: the form field `vote_limit` (a whole number from 1 to 100, not sent = 20, refused with `The vote limit must be a whole number from 1 to 100.` before the file is read),
parsed like `spirograph_notes` (`_parse_vote_limit`), echoed as `vote_limit` for every picture (as the other settings are), checked by `tempo_votes.check_vote_limit` and mirrored by
`validateVoteLimit` on the page. The page gets a group **Rhythm Circles** with one control (`vote-limit`, a slider 1 to 100 with the readout) for this type only, followed by
Held notes (Extra notes) and Local peaks (Minimum distance).

**Rationale**: spec FR-007 and FR-012; the same pattern as every other setting, in the order Spirograph uses.

## Decision 8 - Rhythm Circles joins the held-notes types

**Decision**: `held_notes.HELD_NOTES_TYPES` gets `"rhythm-circles"` (eight types, n = 5), so `notes_of` gives 5, `_parse_extra_notes` limits its Extra notes to 1..5, and the page's
`usesHeldNotes` and `groupsFor` show the Held notes group for it. `frame_rendering` needs no new check of its own (the starts are made in the job, like the measurement).

**Rationale**: spec FR-011; one place decides which pictures have the setting. **Cost**: tests that count the types or spell out the groups change (`test_held_notes.py`
`len(HELD_NOTES_TYPES) == 7`, the groups and validation tests of the frontend, the response-key tests); they are listed in `tasks.md`.

## Decision 9 - Where the starts and the votes are made: in the job, before `write_frames`

**Decision**: the job already makes `average_frames(...)` for `write_frames` and the Rhythm data before it. The job makes the averaged frames **once** into a variable, calls
`rhythm_angles(peaks, fps, frames, values, extra_notes, vote_limit)` (which makes the starts, the votes and the six angle series) and passes the same `values` to `write_frames`.
`write_frames` is unchanged except for its docstring (it still receives a finished `RhythmData`, now `(frames, 6)`).

**Rationale**: no new parameter on `write_frames`; the check `rhythm.frame_count == len(frames)` stays; the local peak measurement still happens once.

**Alternatives considered**: passing the settings into `write_frames` and making the starts there (rejected: it would add two parameters to a function that already has twenty, and
the measurement and `rhythm_angles` are made in the job today).

## Decision 10 - The tempo finder is kept, unused by the picture

**Decision**: `tempo_finder.py` and its tests stay (Polychord's `frame_tempos` uses it); `rhythm_circles.py` stops importing `find_tempo` and takes `START_TEMPO` for the 120.

## Decision 11 - Measured on the two sample files, reported not gated

**Decision**: a tool `specs/047-rhythm-note-voting/tools/verify_votes.py` and a test `test_tempo_votes_files.py` run the whole path (read, analyze, floor, average, starts, votes) on
`backend/audio/sonata.wav` and `almost2.wav` and **report**: the number of starts, the share of starts after the first 10 seconds at which the first or the second tempo is within
10% of 116 (sonata) and of 90 (almost2), the number of changes of the first tempo, and whether two runs are identical; the test asserts only the invariants (18 tempos, votes in
0..limit, deterministic) and skips when a file is missing, as `test_tempo_files.py` does for spec 040.

**Rationale**: SC-006; the tolerance of Decision 3 makes many tempos fit a short length and only the measurement shows how well the voting separates tempos on real music; if it
does badly the levers are the tolerance (FR-006), the vote limit and the note values, all one constant each.

## Decision 12 - The other types are unchanged and checked against a baseline

**Decision**: nothing in `local_peaks.py`, `tempo_finder.py`, `polychord.py` or the other pictures changes. The frames of every other type are compared with a baseline made before
the work (`specs/041-code-readability-docs/tools/verify_frames.py`), and the angles of the two local-peak circles of Rhythm Circles are compared with columns 2 and 3 of the old angles (the same numbers; the rings move,
so the pictures are not compared pixel by pixel). The full backend run is compared with `baseline-failures-before.txt` (the 32 known failures).

## Decision 13 - Measured on the two sample files (2026-11-25, reported, not gated)

`tools/verify_votes.py` (output kept in `verify_votes-output.txt`; 30 frames a second, Extra notes 2, time resolution 60 ms, the starts after the first 10 seconds):

| File | Starts | Target | First tempo within 10% | First or second within 10% | Changes of the first tempo |
|------|--------|--------|------------------------|----------------------------|----------------------------|
| `sonata.wav`, limit 5 | 1,729 | 116 | 58% | 59% | 509 |
| `sonata.wav`, limit 20 | 1,729 | 116 | 64% | 65% | 439 |
| `sonata.wav`, limit 100 | 1,729 | 116 | 64% | 65% | 439 |
| `almost2.wav`, limit 5 | 1,862 | 90 | 14% | 20% | 610 |
| `almost2.wav`, limit 20 | 1,862 | 90 | 14% | 19% | 594 |
| `almost2.wav`, limit 100 | 1,862 | 90 | 14% | 19% | 594 |

Reading: on `sonata.wav` the voting finds the beat about two thirds of the time (the old tempo finder: 49%); on `almost2.wav` it does not find 90 (14 to 19%; the old finder 35%): the
beats in groups of four at about 180 are a hard case for any rule that votes on the spacing of notes, because the notes come at every level between the beat and the sixteenth. The first
tempo changes about every four starts, so the outer ring is not steady. Limits 20 and 100 are the same on both files because the votes seldom reach 20 (the tolerance is wide: at 60 ms a
0.25 s length fits 16 of the 18 tempos, so many tempos rise together and the ranking among them falls to the tie rule, the lower tempo). The levers, each one constant or argument, if the user
wants it better: the tolerance of `fitting_tempos()` (the resolution term, `HALF_BIN`), `NOTE_BEATS`, the vote limit, and the number of loudest notes (5). Nothing was tuned: the rule is the one
written in the spec.

## Decision 15 - Points by note value, and starts from the 60 ms windows (2026-11-25, second round)

The user tried the first version on `almost2.wav` (15 frames a second, vote limit 10, Extra notes 4) and found it close for the first two minutes, then asked why the frame rate should matter at all and for **points by note value**: 2 for the plain notes, 1 for dotted ones, so that fewer tempos share the same vote. Both are done:

- `tempo_points()` gives each fitting tempo the most points of the note values that fit it: 2 for 2, 1, 1/2, 1/4 beats; 1 for the dotted values and for the two triplets (`PLAIN_POINTS`, `DOTTED_POINTS`, `TRIPLET_POINTS`). 60/92 s gives 92 two points and 136 and 140 (a dotted quarter at 138) one; half as long gives the same plus 124 (a triplet). A tempo that only dotted notes or triplets fit stays at 1 vote under a steady spacing.
- `rhythm_angles()` takes the 60 ms windows (`result.frames`) and finds the starts there with a fixed 60 ms resolution; the frame rate only chooses the moments at which the finished step functions are sampled (test: the same windows at 10 and 30 frames a second give the same six angles at the same moments).

**What was measured** (reported, not gated; Extra notes 4, vote limit 10, share of starts after 10 s whose first tempo is within 10% of the target):

| Starts from | almost2 (target 90) | sonata (target 116) |
|---|---|---|
| frames at 30 fps, flat 2 points (version 1, Extra 2 limit 20) | 14% | 64% |
| frames at 30 fps, new points | 23% | 42% |
| frames at 15 fps, new points | 27% | 18% |
| 60 ms windows, new points (this version) | 2% | 31% |

The windows are worse than the frames: 64% of the gaps between starts of the loudest notes are exactly one window (60 ms), the same note counted again when a neighbouring column (the bass is blurred across about three semitone columns by the 4096-sample window) or the same column re-enters the selection, and on a 60 ms grid a 0.333 s note length is measured as 0.30 or 0.36 s, which votes for 100 and 84 bpm. At 15 frames a second a 90 bpm eighth note is exactly 5 frames (0.333 s), which is why 15 fps looked right on this file: luck of the grid, not a better tempo. The next step the user considered is onsets from energy rises per register; a minimum gap between starts of 0.10 s gave a steady 100 bpm on almost2 (not tried in the code).

## Decision 14 - The group id of the page (2026-11-25)

The page group of the Vote limit has the id `rhythm-circles` (the name of the image type), not `rhythm` as the first draft of `tasks.md` said: the page shows the group of a type by the
rule `TYPE_GROUPS.includes(imageType)`, which needs the id to equal the image type.

## Decision 16 - The average tempo (2026-11-26)

The first tempo jumps, so the user asked to try the **straight average of the previous 5 tempos** as a baseline (a weighted average with the newest tempo 2x was also asked about; it was measured and not used). The average is of the first tempo after each start and the 4 before it (fewer at the start), `AVERAGE_COUNT = 5`, and it replaces the second tempo as a circle: (1) average, (2) its rate of change, (3) raw first tempo, (4) its rate of change.

Measured offline (60 ms windows, points as in Decision 15, Extra notes 4, limit 10, starts after 10 s, tempo within 10% of the target; raw / straight average): `almost2.wav` 2% / 14%, `sonata.wav` 31% / 33%, `piano-108bpm.wav` 58% / 74%, `piano2-108bpm.wav` 44% / 59%, `piano-120bpm.wav` 30% / 24%. The newest-2x weighting scored 1 to 3 points above the straight average on `almost2.wav` and `sonata.wav`, and the straight average steadies most (the mean change per start falls from about 6 to 2.5 beats per minute). The average of every file sits at 100 to 107 beats per minute, near the middle of the range, so it steadies the circle without making the tempo right. On the three piano files (computer-generated, steady) 49 to 65% of the gaps between starts are one 60 ms window: the starts, not the voting, are the weak part, and are the next piece of work. A minimum gap between starts was tried offline (0.10 s: 97% on the 108 bpm files and 2% on the 120 bpm file; 0.15 s: about 0%) and was not adopted: the result depends on how the gap meets the grid and the note values.
## Decision 17 - The starts from the rise, placed on the waveform (2026-11-26, fourth round)

**Problem.** The tempo is voted on the time between starts, and the starts of the first three rounds (entries into the held 5 loudest notes, on the 60 ms windows) were wrong in two ways found with the seven single-note piano samples (`backend/samples/piano-p-c1.wav` to `c7`), cut and joined into sequences with silence between and known onsets: they were found **3 to 5 times too often** (the onset of a note leaks into the neighbouring semitones for about 0.4 s, and as a note dies away, notes that were below the top 5 + k rise into the selection), and they were only known to a window (a systematic offset of about -29 ms against the true onset).

**Decision.**
1. `note_onsets.onset_rises`: per window, the sum over the 84 notes of the rise of the note over the larger of its strength in the 2 windows before (never below 0).
2. `note_onsets.pick_onsets`: a window is a start when its rise is above 0, the largest within 2 windows either side, and at least 20% of the largest within 33 windows (2 s) either side; two starts less than 2 windows apart are one (the larger rise, the earlier when equal). On the synthetic sequences this finds nearly every onset with no doubles and few strays.
3. `note_onsets.refine_starts`: each start moves to the frame of largest rise of the root-mean-square level of the mix `(left + right) / 2` (frames of 512 samples every 128), searched from 0.10 s before to 0.05 s after the window's middle (a start with no rise stays); starts that land within 30 ms of the one kept before are one. The error of a start against the true onset goes from a mean of about -29 ms (window-middle) or +9 ms with 24 ms spread (rise peaks) to under 5 ms.
4. The fit resolution of the voting is 40 ms (`rhythm_circles.START_RESOLUTION`; half of it, 20 ms, is the tolerance of the second way a length fits). Starts from the rise on the 60 ms grid alone did not help on real files (a 30 ms tolerance is too wide for short gaps); the placement on the waveform and the 40 ms together did.
5. `rhythm_angles` takes the two channels (`left`, `right`, with the sample rate of `peaks.file_rate`) and no longer takes the Extra notes; the job passes `left, right`. `tempo_votes.note_starts` is deleted (nothing used it); `held_notes` is unchanged for the seven other pictures except that `HELD_NOTES_TYPES` no longer lists `rhythm-circles` (so `notes_of` gives 8 for it, as for Contour). The page loses the Extra notes control and the Held notes group for this type.
6. Chosen on these files: the threshold 20%, the 40 ms resolution, the window of 0.10 s before and 0.05 s after, the 30 ms merge. They were tried at a few values on the same five files and are not validated on other music.

**Memory and time.** The waveform is read only around each start (about 0.15 s each), so no copy of the whole file is made: 5 to 30 ms for the test files.

**Measured** (`tools/verify_votes.py`, output in `verify_votes-output-4.txt`; tempo within 10% of the target for the starts after 10 s; raw / average of 5): at limit 20 `sonata.wav` 97 / 99%, `almost2.wav` 67 / 75%, `piano-108bpm.wav` 100 / 100%, `piano2-108bpm.wav` 100 / 100%, `piano-120bpm.wav` 75 / 67%. With the starts of the held notes (limit 10, from the third round) they were 31 / 33, 2 / 14, 58 / 74, 44 / 59 and 30 / 24%.

**Alternatives considered.** Per-register detection (not tried); a per-start threshold of the number of notes that rise (not needed); keeping Extra notes as a setting that does nothing (a control that does nothing is misleading, so it is removed from the page).

## Decision 18 - Trills, the last 2 starts, a beat divided in 2 or 3, a tie keeps the tempo (2026-11-27, fifth round)

**Problem.** On `Thunderer.wav` (a march at 120 to 124 bpm) the fourth round had the tempo in the 120 or 124 bin for 58% of the starts. The user heard the unstable places (4 to 8 s, 20 to 25 s) and named trills in the flutes and piccolos. Looking closer: the beats were all found there, but notes between the beats (lower instruments off the beat, 200 to 210 ms on one side and 280 ms on the other instead of the even 242 ms) fitted no tempo and took a vote from every tempo at each start, so the votes of the right tempo fell from 3 to 7 to 1 to 3 and ties went to 72 or 76. The vote totals never came near the limit of 20.

**Decision.**
1. `trills.py` (new): the semitone levels from C3 to G#7 every 256 samples (frames of 2048, a Hann window, `log10(1 + energy)`); around each 60 ms window (0.5 s of levels) the best pair of notes 1 or 2 semitones apart that both sound (mean level above the 60th percentile) scores `max(-correlation of their flicker, 0) x the smaller share of their flicker at 6 to 20 times a second`; windows scoring 0.2 or more, joined across gaps of up to 3 windows and at least 3 long, are a trill, widened by 4 windows (0.24 s) at each end (the score looks half a second around its window, so it rises a quarter of a second late and falls as early; widening measured the same at 10% and better for the sonata at 3%). The trills were found where the user heard them (Thunderer 4.6 s, 8.5, 10.5, 12.3, 16.2, 20 s and the repeats, sonata 8.24 to 9.3 s) and none in the three computer-made piano files; the trill's overtones flicker too and are covered by "the lowest note upward". The 60 ms windows cannot see a trill: its notes are 60 to 80 ms long and blur into one sound.
2. `note_onsets.onset_rises(values, spans)`: within a trill the notes from one semitone below its lowest note upward make no rise. Placing a start inside a trill on the waveform below the trill (the transform cut there) was tried and measured worse (Thunderer 3% band 94% to 76%), so a start is placed on the whole waveform as before.
3. `tempo_votes.vote_tempos(..., meter, lookback)`: with `lookback` 2 a start votes with its time since each of the last 2 starts, the best points per tempo. 3 or 4 starts back were worse (sonata 48% and 20%).
4. A second note table for a beat divided in 3 (`TRIPLE_NOTE_BEATS`); `meter_tempos` chooses the meter whose best tempo has more votes (an equal best keeps the meter) and its tempo (the tempo before when it is one of the equal best). Requiring a lead of 5, 10, 15 or 20 votes to change the meter was tried: no lead kept both `piano-120bpm.wav` (needs the change) and `02_Mean_.wav` (must not change).
5. A tie keeps the tempo (the user's "stick with the tempo from before"); the default vote limit is 40 (with two lengths a start gives more points and 20 was reached too soon; taking 2 votes a start instead was much worse).

**Measured** (`tools/verify_votes.py`, `verify_votes-output-5.txt`; first tempo within 10% of the target for the starts after 10 s, in brackets within 3%): `sonata.wav` 97% (3% band 51%), `almost2.wav` 97% (32%), `piano-108bpm.wav` 100% (82%), `piano2-108bpm.wav` 100% (91%), `piano-120bpm.wav` 90% (90%), `Thunderer.wav` 100% (94%), `WMTS.wav` 92% (84%), `turnyourlove.wav` 88% (66%), `02_Mean_.wav` 32% (32%). In the fourth round (limit 20): 97%, 67%, 100%, 100%, 75%, 76%, 100%, 100% and 84% within 10%, and Thunderer 58% within 3%.

**Caveats.** Every value (the trill score 0.2, the widening, 2 starts, limit 40, the meter rule) was chosen on these nine files. The meter is only recognized from rhythms that the other reading fits worse: even 6/8 eighths at 120 (1/6 and 1/3 s) are also a sixteenth and an eighth of 88 within the 20 ms tolerance. Syncopated pop (`02_Mean_.wav`, about 105) is read as a beat of 140 divided in 3 (its dotted eighths are whole beats there); a listener decides the meter over several bars from where the strong beats fall, which is the next idea (the meter from the strong low starts, or over a longer stretch).
