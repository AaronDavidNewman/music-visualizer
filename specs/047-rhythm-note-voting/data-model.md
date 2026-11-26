# Data Model: Rhythm Circles Tempo Voting

Feature 047. Every array has its alias and description in `backend/app/services/array_types.py` (constitution rule II) before it is used in a signature; the aliases below
marked **new** are added, the others are reused or widened.

## Constants (`tempo_votes.py`)

| Name | Value | Meaning |
|------|-------|---------|
| `TEMPOS` | `72 + 4n`, n = 1..18 (76, 80 ... 144) | the 18 tempo bins, beats per minute |
| `NOTE_BEATS` | `(2, 1, 1/2, 1/4, 3, 3/2, 3/4, 3/8, 1/3, 2/3)` | the lengths in beats of a half, quarter, eighth and sixteenth note, each dotted, and the two triplets |
| `HALF_BIN` | `2.0` | beats per minute: half the distance between two bins |
| `SLACK` | `1e-9` | added to the inclusive comparisons so that exact cases are inclusive in floating point |
| `DEFAULT_VOTE_LIMIT` | `20` | the vote limit when a job does not say |
| `MIN_VOTE_LIMIT`, `MAX_VOTE_LIMIT` | `1`, `100` | the range of the setting |
| `VOTE_LIMIT_MESSAGE` | `The vote limit must be a whole number from 1 to 100.` | the refusal |
| `NO_VOTES_TEMPO` | `tempo_finder.START_TEMPO` (120) | what a place without votes holds |

## Settings

| Setting | Type | Allowed | Default | Where |
|---------|------|---------|---------|-------|
| `vote_limit` | `int` | whole number 1 to 100 (a bool, a string, a fraction or a non-finite number is refused) | 20 | request field `vote_limit`, echoed as `vote_limit`, page slider `vote-limit` |
| `extra_notes` | `int` | 1 to 5 for this type (its n is 5) | 2 | the existing field; Rhythm Circles joins `HELD_NOTES_TYPES` |

## Arrays

| Alias | Shape | Meaning | Made by |
|-------|-------|---------|---------|
| `NoteStrengths` (reused) | `(frames, 88)` | the strength of each note in each frame; the first 84 columns are the notes | `average_frames` |
| `LoudestIndices` (reused) | `(frames, 5)` | the note at each of the 5 places of each frame, loudest first, held notes among them | `held_notes.hold_loudest` |
| `StartTimes` **new** | `(starts,)` | the time in seconds, from the start of the file, of the middle of each frame in which a sounding loudest note enters the selection; strictly increasing, the first is the first start | `tempo_votes.note_starts` |
| `TempoVotes` **new** | `(starts, 18)` | the votes of each of the 18 tempos (axis 1, tempos 76 to 144 in steps of 4) after each start (axis 0): whole numbers 0 to the vote limit, row 0 all 0 | `tempo_votes.vote_tempos` |
| `FitMatrix` **new** | `(cycles, 18)` | true where the note length of a cycle fits the tempo (a boolean); one row for each start after the first | `tempo_votes.fitting_tempos` |
| `AveragedTempos` **new (third round)** | `(starts,)` | the straight average of the first tempo (column 0 of `RankedTempos`) after each start and the 4 starts before it, fewer at the beginning, in beats per minute | `tempo_votes.average_tempos` |
| `RankedTempos` **new** | `(starts, 2)` | after each start, the tempo with the most votes (column 0) and the next (column 1), in beats per minute; a place with 0 votes holds 120 | `tempo_votes.ranked_tempos` |
| `CircleSeries` (widened) | `(events, circles)` | the speeds after each event in revolutions per minute: for the vote circles `(starts, 4)`: first tempo, its change, second tempo, its change; for the peak circles `(peaks, 2)`: the peak's rate, its change | `tempo_votes.vote_series`, `rhythm_circles.peak_series` |
| `CircleSpeeds`, `CircleAngles` (widened) | `(moments, circles)` | the speed / the angle in turns of each circle at each moment; the width is that of the series (4, 2, or 6 once joined) | `circle_speeds`, `circle_angles` |
| `Moments` (reused) | `(frames,)` | `(f + 0.5) / frame_rate` seconds | `rhythm_angles` |

`RhythmData.angles` is `CircleAngles (frames, 6)`: the columns are the rings from the outside in: average tempo, its change, raw first tempo, its change, local peak, its change (the second tempo is not drawn).

## Rules (the voting)

For starts `s_0 < s_1 < ... < s_m`, the **cycle** `i = 1..m` has the length `L_i = s_i - s_{i-1}`.

- `fit[i, t, b] = ( |60 b / L_i - T_t| <= 2 + SLACK or |60 b / T_t - L_i| <= resolution / 2 + SLACK )` for each `b` in NOTE_BEATS; `NOTE_POINTS[b]` is 2 for 2, 1, 1/2, 1/4 beats and 1 for the dotted values and the triplets.
- `points[i, t] = max over b of ( NOTE_POINTS[b] * fit[i, t, b] )` (0 where nothing fits; the most, not the sum).
- `votes_0 = 0` (18 zeros); `votes_i = clip( clip(votes_{i-1} - 1, 0, limit) + points[i], 0, limit )` (and only where `points > 0`), i.e. one is taken from every tempo (not below 0), then each fitting
  tempo gets its points (not above the limit).
- `ranked_i`: the tempos ordered by `votes_i` descending, ties by the lower tempo; the first two; a place with `votes = 0` holds 120.
- The levels of the vote circles after start `i` are `ranked_i[0]` and `ranked_i[1]`; their change is `(level_i - level_{i-1}) / (s_i - s_{i-1})`, 0 for `i = 0`.
- Before the first start, and with no start at all, the vote circles' speeds are `(120, 0, 120, 0)`; the peak circles' `(60, 0)`: `DEFAULT_SPEEDS = (120, 0, 120, 0, 60, 0)`.
- `resolution = 0.06` seconds in a job (the starts are found in the 60 ms windows, whatever the frame rate); 0 in tests of exact start times.

## Entities

- **Start**: see `StartTimes`; **Cycle**: one per start after the first; **Tempo bin**: one of `TEMPOS`; **Vote limit**: the setting; **First and second tempo**: `RankedTempos`
  columns (spec Key Entities).
- **RhythmData** (existing, frozen): `angles` `(frames, 6)`; `frame_count`.
