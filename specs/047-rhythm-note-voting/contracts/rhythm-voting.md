# Contract: Rhythm Circles tempo voting

Feature 047. The request, the response, the library and the picture.

## Request (`POST /api/jobs`)

| Field | Type | Allowed | Default | Refusal (400, before the file is read, no files left) |
|-------|------|---------|---------|-------------------------------------------------------|
| `vote_limit` | form text | a whole number 1 to 100 | 20 | `The vote limit must be a whole number from 1 to 100.` |
| `extra_notes` | form text | for `image_type=rhythm-circles` 1 to 5 (its n); the other types as before | 2 | `The extra notes must be a whole number from 1 to 5.` |

`vote_limit` is checked for every image type and used by Rhythm Circles only (as `spirograph_notes` is). `peak_distance` (Minimum distance) still applies to Rhythm Circles (the
local peak circles); `peak_prominence` is still ignored. Every other setting is accepted, checked and ignored for this type as before.

## Response

The job answer gains `"vote_limit": <int>` for every picture (the limit used; 20 when not sent). `extra_notes` and `peak_distance` are echoed as before. No other key changes.

## Library (`backend/app/services/tempo_votes.py`, pure functions)

| Function | Returns | Notes |
|----------|---------|-------|
| `check_vote_limit(value: object) -> int` | the limit | `ValueError(VOTE_LIMIT_MESSAGE)` for a bool, a string, a fraction, a non-finite number or a value outside 1..100 |
| `note_starts(values: NoteStrengths, extra: int, frame_rate: float) -> StartTimes` | `(starts,)` seconds | the held loudest 5 of the first 84 columns; a start when a sounding selected note enters; one start per frame |
| `fitting_tempos(lengths: ArrayLike, resolution: float) -> FitMatrix` | `(cycles, 18)` bool | spec FR-006: the tempos that any note value fits |
| `tempo_points(lengths: ArrayLike, resolution: float) -> TempoPoints` | `(cycles, 18)` int 0, 1, 2 | 2 for a tempo that a plain note fits, 1 if only a dotted note or a triplet fits, the most and not the sum (second round) |
| `vote_tempos(start_times: ArrayLike, resolution: float, limit: int) -> TempoVotes` | `(starts, 18)` | spec FR-003 and FR-004 |
| `ranked_tempos(votes: ArrayLike) -> RankedTempos` | `(starts, 2)` | ties lower first; 0 votes holds 120 |
| `average_tempos(tempos: ArrayLike) -> AveragedTempos` | `(starts,)` | straight mean of the latest 5 (all there are at the beginning) |
| `vote_series(start_times: ArrayLike, levels: ArrayLike) -> CircleSeries` | `(starts, 4)` | levels `(starts, 2)` (average, raw) and their changes |

`rhythm_circles.rhythm_angles(peaks, frame_rate, frames, windows, extra_notes, vote_limit) -> RhythmData` makes the six columns; `windows` are the 60 ms analysis windows `(windows, 88)` (any number
of rows, not the frames), so the voted tempos do not depend on the frame rate. Wrong inputs (a bad frame rate, a windows array that is
not a 2-D array of at least 84 non-negative columns, an extra or limit not allowed) are refused with `ValueError`, nothing partial is returned. `circle_speeds` and `circle_angles` take `defaults` (default
`DEFAULT_SPEEDS`, the six speeds before the first event).

## Picture (`rhythm-circles`)

Six concentric rings, centered, from the outside in: **average tempo** (of the last 5 first tempos), **its rate of change**, **raw first tempo**, **its rate of change**, **local peak**, **its rate of change**.
Each ring is `outer / 6` wide less the gap on its inner side (`outer = min(width, height) / 2 - 10`); ring `k` (1 outer to 6 inner) has the colormap row `rint((k - 1) / 5 x 255)`
and its notch the row `rint((1 - (k - 1) / 5) x 255)`; the notch is an eighth of the circle; a tempo ring turns at as many revolutions per minute as the tempo has beats per minute,
clockwise positive; a rate-of-change ring at the change in beats per minute per second taken as revolutions per minute; the angle is the running total of `speed / 60`, so a
notch never jumps. A speed is constant between two events (starts for the first four rings, peaks for the last two). The frames' names, size and count are those of the other types.

## Page

Group **Rhythm Circles** (group id `rhythm-circles`, this type only): slider **Vote limit** (1 to 100, step 1, default 20, readout the number) with an info text; then **Held notes** (Extra notes, 1 to 5) and
**Local peaks** (Minimum distance, no checkbox). The result summary shows the Vote limit for this type. The other types show none of this.

## Fourth round (2026-11-26): `note_onsets`

| Function | Returns | Rule |
|----------|---------|------|
| `onset_rises(values) -> OnsetRises` | `(windows,)` | the summed rise of the 84 notes over the larger of the 2 windows before |
| `pick_onsets(rises) -> StartTimes` | `(starts,)` seconds | peaks: largest within 2 windows, at least 20% of the largest within 33 windows; under 2 windows apart: the larger |
| `refine_starts(starts, left, right, sample_rate) -> StartTimes` | `(starts,)` seconds | each start moves to the largest rise of the waveform level from 0.10 s before to 0.05 s after; within 30 ms of the one before: dropped |
| `onset_starts(values, left, right, sample_rate) -> StartTimes` | `(starts,)` seconds | `refine_starts(pick_onsets(onset_rises(values)), ...)` |

`rhythm_angles(peaks, frame_rate, frames, windows, left, right, vote_limit)`; the fit resolution is `rhythm_circles.START_RESOLUTION` (0.04 s). `tempo_votes.note_starts` no longer exists. The Extra notes setting is accepted (1 to 8) and ignored for Rhythm Circles.

## Fifth round (2026-11-27)

| Function | Returns | Rule |
|----------|---------|------|
| `trills.find_trills(left, right, sample_rate, windows) -> TrillSpans` | `(spans, 3)` | `trill_spans(*trill_scores(semitone_levels(left, right, sample_rate), sample_rate, windows))` |
| `note_onsets.onset_rises(values, spans=()) -> OnsetRises` | `(windows,)` | as before, without the notes from one semitone below each trill's lowest note upward inside it |
| `note_onsets.onset_starts(values, left, right, sample_rate)` | `(starts,)` | finds the trills first; otherwise as before |
| `tempo_votes.vote_tempos(starts, resolution, limit, meter=2, lookback=1)` | `(starts, 18)` | with `lookback` k the best points of the times since each of the last k starts; `meter` 3 the note values of a beat divided in 3 |
| `tempo_votes.meter_tempos(votes) -> MeterTempos` | `(starts, 2)` | the meter whose best tempo has more votes (equal: stays); its tempo with the most votes, the tempo before when among the best |
| `tempo_votes.leading_tempos(starts, resolution, limit) -> MeterTempos` | `(starts, 2)` | both meters with `LOOKBACK` 2, then `meter_tempos`; Rhythm Circles takes column 0 |

The request field `vote_limit` defaults to 40 (was 20); everything else in the request and the answer is unchanged.
