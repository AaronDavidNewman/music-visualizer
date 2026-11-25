# Research: Spirograph

Phase 0 of the plan. Every unknown of the Technical Context is settled here; none is left open.

*Update 2026-11-24: Decision 14 changes the formula (loops by the letter, `rc` and the turns by the place in the local peak), the extent and the line widths of Decisions 2, 3 and 13.*

## Decision 1 - Where the history lives

**Decision**: no stored history. `tracked_notes()` makes the whole file's `TrackedValues` `(frames, count)` and
`LoudestIndices` `(frames, count)` once, and the picture of frame `t` slices the rows `max(0, t - history + 1)` to `t`.

**Rationale**: the user keeps "a history of both the bin values and the bin indices" with an outer loop over the history and an
inner loop over the notes. The history of frame `t` is just the tracked notes of frames `t - history + 1` to `t`, and those
rows exist already; a deque filled frame by frame would give the same numbers and could not be drawn by several threads, nor
tested without running the frames before. Row `i` of the slice is the user's `binValueHistory[i]` and `binIndexHistory[i]`;
column `j` is the `j`-th note; so `val = values[i, j]` and `bc = indices[i, j] / 84` come from the same entry, as the user
answered.

**Alternatives considered**: a `collections.deque` of the last `history` entries updated in a frame loop (serial, same result,
rejected for threading and testability); history in seconds instead of frames (rejected: the user said "between 5-12 previous
bins", and the spec counts entries, so it is frames, whatever the frame rate).

## Decision 2 - The tracked notes

**Decision**: `held_notes.hold_loudest(values[:, :84], count, extra)` gives `LoudestIndices` `(frames, count)` (loudest first,
held notes among them, padded with zero-strength notes when fewer sound). The value of a slot is the square root (revision 2026-11-21: the pictures were small most of the time) of the note's strength over the
file's peak (`values.max()` over all 88 columns, the `peak` that `write_frames` uses), so the loudest note of the file is 1 and
a padded slot is 0 (nothing is drawn for it).

**Rationale**: the same selection Polychord and Decay use, so Extra notes (feature 044) works unchanged and ties go to the
lower note. Dividing by the whole file's peak is what makes `yval = 12 val` fall from 0 to 12, which the color index expects.

**Alternatives considered**: normalising each frame by its own loudest note (rejected: the picture would lose loudness
differences between frames, and a faint frame would look as strong as a loud one); normalising by the loudest of the 84 drawn
notes only (rejected: the spec says the loudest note of the whole file; the difference is only when one of the four highest
notes, 84 to 87, is the file's loudest).

## Decision 3 - The curve

**Decision**: `spiro_curves(values, indices)` returns `SpiroCurves` `(curves, 1000, 2)` in units: with `c1 = np.linspace(0, 2 pi,
1000)` and `c2 = np.linspace(0, 14 pi, 1000)` (both inclusive), `X = val (5 cos c1 + bc yval cos c2)` and `Y` the same with sines,
`yval = 12 val`, `bc = index / 84`, all vectorised over the curves.

**Rationale**: it is the user's formula, with `rc` the constant 5 (the user's answer). Both angles advance together, so the small
circle turns seven times while the pen goes once round the big one: a closed curve with seven loops.

**Alternatives considered**: none; the formula is given.

## Decision 4 - The reduced colors and the color of a curve

**Decision**: `reduced_colors(colormap)` returns `ReducedColors` `(13, 3)` `uint8`: row `k` is the colormap's lookup-table row
at `min(255, floor(sqrt(k / 12) x 256))` (the user's `(linspace(0, 1, COLOR_BINS + 1) ** 0.5) x 256` with `COLOR_BINS` 12;
position 256 is past the end of a 256-row table and takes the last row). `color_numbers(values)` returns `ColorNumbers`:
`min(floor(12 val + 1e-9), 12)`; the small epsilon keeps `m / 12 x 12` from falling to `m - 1` by rounding.

**Rationale**: spec FR-007 and scenarios 3 and 4. `colormaps.lookup_table` and `COLORMAP_STEPS` are what Polychord's
`tempo_colors` uses, so every colormap offered works.

**Alternatives considered**: interpolating between the reduced colors (rejected: the user wants a reduced number of colors); an
`int(round(...))` for the number (rejected: the user's `min(yval, size)` is a floor).

## Decision 5 - One fixed scale and the extent of a file

**Decision**: the farthest point of a curve from the center is the first (`c1 = c2 = 0`, both cosines 1, sines 0), at
`val x (5 + bc x yval)`, because by the triangle inequality `|5 e^(i c1) + A e^(i c2)| <= 5 + A` and the first point reaches it.
`file_extent()` is the maximum of that over every tracked value and index of the file (0 when nothing sounds);
`pixels_per_unit()` is `(min(width, height) / 2 - MARGIN - LINE_WIDTH) / extent`, so the largest curve of the file just fits,
the pattern is centered and round, and the scale does not change from frame to frame. A silent file has extent 0 and draws
nothing, so no division happens.

**Rationale**: spec FR-008 and SC-006. The bound is exact, so no sampling of 1000 points for every note of every frame is
needed, and "nothing outside the picture" holds by construction at any size (a size too small for the margin is refused, as
Polychord refuses one).

**Alternatives considered**: a scale per frame (rejected: a quiet frame would be blown up and the picture would pulse); a fixed
scale from the largest possible curve, 5 + 12 x 83/84 = 16.86 (rejected: a typical file's loudest tracked note has a smaller
extent, so the pictures would be small); stretching to the 3:2 shape (rejected: the spirograph is round).

## Decision 6 - Extra notes with up to 12 notes

**Decision**: Spirograph is added to `HELD_NOTES_TYPES`; `notes_of(image_type, polar_notes, polychord_notes,
spirograph_notes=MAX_EXTRA_NOTES)` returns `min(spirograph_notes, MAX_EXTRA_NOTES)` for it, so **k is 1 to the smaller of the
number of notes and 8**; `MAX_EXTRA_NOTES` stays 8. The frontend's `heldNotesCount(imageType, polarNotes, polychordNotes,
spirographNotes)` does the same. The job's default k (2) applies when the request does not say.

**Rationale**: raising `MAX_EXTRA_NOTES` to 12 would change the page's slider for every type, the checks and many tests of
feature 044 for no wish of the user's. A k above 8 for a figure of 9 to 12 notes is not useful: 8 extra places already hold a
note until it falls to rank 17 to 20. The fourth parameter has a default so that the callers that do not know the new type
(the other types, the tests of 044) are unchanged.

**Alternatives considered**: raise the maximum to 12 (rejected, above); leave Extra notes out for this type (rejected: the spec
and the user's wish for a smooth flow want it).

## Decision 7 - The drawing

**Decision**: one `Figure` (no `pyplot`) per picture, axes filling it in pixel units with y down (the pattern's `Y` is up, so
pixel `y = height / 2 - scale x Y`), one `LineCollection` whose segments are the curves (each `(1000, 2)`), `colors` the color
of each curve from the reduced set, `linewidths` one value `max(1.0, height / 1000)` pixels as points (`x 72 / 100`),
anti-aliased, `capstyle`/`joinstyle` round; drawn with `FigureCanvasAgg`, copied to a `uint8` array `(height, width, 3)`, saved
with `compress_level=1` on a few threads (`SAVE_WORKERS`), as Polychord does.

**Rationale**: the same method as `polychord._frame()`, proven deterministic and thread-safe (feature 042); the collection keeps
the order of the loops, so the newest entry and, inside it, the quieter notes are on top, as the spec's drawing order says
(oldest first, loudest first inside an entry means later, quieter curves lie over earlier ones).

**Alternatives considered**: `pyplot` (rejected: not thread-safe); drawing with Pillow's `ImageDraw.line` (rejected: no
anti-aliasing, different look from the other types); one `plot()` call per curve (rejected: 144 artists a frame).

## Decision 8 - No measurement for the job

**Decision**: `create_job()` does not measure the local peaks for Spirograph: the picture needs neither the beat nor the tempo.
The page shows no Local peaks group for it, and Minimum distance is accepted and ignored.

**Rationale**: spec Story 3 says the settings of other types are accepted and ignored; measuring would cost time for nothing.
It also keeps the job's behavior for the other types untouched.

**Alternatives considered**: reuse the beat to scale or fade the curves (rejected: not asked for).

## Decision 9 - Speed

**Decision**: measure first, in the tests: the largest picture (12 notes, history 12, 600 x 400) must take under 2 seconds, and a
300-frame job at the defaults must finish; the plan expects about 0.1 to 0.3 s a picture (144 polylines of 1000 points in the
Agg renderer). If it is slower, the curve is drawn from fewer points only as a plan change that goes back to the user; the 1000
steps are the user's number and are not shortened silently.

**Rationale**: SC-008, and the unknown is real (Polychord's probe was 10 ms for 576 short segments, a different load).

**Alternatives considered**: pre-computing the curves of a file once for all frames and reusing them across history windows
(a note's curve does not depend on the frame): kept as an easy optimisation if needed, because consecutive pictures share all but one
entry (cache `SpiroCurves` per frame, `(frames, count, 1000, 2)` would be 24 MB per 1000 frames at 12 notes, so the cache would
be per picture row instead). Not needed unless Decision 9 fails.

## Decision 10 - The two settings and their wiring

**Decision**: form fields `spirograph_notes` and `spirograph_history` (whole numbers 5 to 12, defaults 8 and 8) and, added 2026-11-22 (Decision 12), `spirograph_fade` (a number 0.4 to 0.85, default 0.7), parsed in
`jobs.py` like `polychord_notes` (a value not sent takes the default; anything else that is not allowed is a 400 with the
message of that setting, before the file is read), carried by a frozen `SpirographSettings(notes, history)` checked by
`check_spirograph_settings()` for every image type in `write_frames`, echoed as `spirograph_notes` and `spirograph_history` for
every type. The messages are `The number of spirograph notes must be a whole number from 5 to 12.` and `The history length must
be a whole number from 5 to 12.` (Polychord's `The number of notes ...` is for 5 to 8, so a refusal says which picture it is for.)

**Rationale**: the same pattern as Polychord's four fields, so the five exact-key API tests gain two keys the way they gained
`export_obj` and `obj_url` in feature 045.

**Alternatives considered**: sharing `polychord_notes` (rejected: different range, different picture).

## Decision 11 - The page

**Decision**: option `{ value: "spirograph", label: "Spirograph" }` after Polychord; group `spirograph` (title "Spirograph",
controls `spirograph-notes`, `spirograph-history`, two sliders 5 to 12 like Polychord's), then `held-notes`; no `concentric-peaks`
and no `local-peaks`, no note layout, no 3D export, no image smoothing; help texts `spirographNotesHelp` and
`spirographHistoryHelp`, a `Spirograph:` paragraph in `imageTypeHelp`, and Spirograph named in the Extra notes help; the result
list shows both settings for the type.

**Rationale**: the pattern of feature 042's page; the group list of `groupsFor()` is data tested in `groups.test.ts`.

**Alternatives considered**: none.

## Decision 12 - History fade (added 2026-11-22)

**Decision**: a third setting `fade` (field `spirograph_fade`, a number from 0.4 to 0.85, default 0.7, message `The history fade
must be a number from 0.4 to 0.85.`) in `SpirographSettings` (with a default, so `SpirographSettings(notes, history)` still
works). `window_curves(..., fade=DEFAULT_FADE)` multiplies the values of the window's rows by `fade ** age`, `age` being
`frame - row` (0 for the frame's own row), before `spiro_curves()` and `color_numbers()`; the indices are untouched. The page has a
slider 0.4 to 0.85 in steps of 0.05 (readout `0.7 per frame`) after History length; the answer has the key `spirograph_fade`.

**Rationale**: the user wants the current frame more prominent. Compounding gives a smooth fade over up to 12 entries; at 0.85 the
oldest of 12 is still 0.17 of its value, at 0.4 the entries before the third are almost gone (0.4 ** 3 = 0.064). The scale does
not change: the farthest point of a faded curve is at most that of the unfaded one, and the newest entry is whole.

**Alternatives considered**: one flat factor on all older entries (less of a gradient; a one-line change if wanted); fading
only the size and not the color number (rejected: the user said to multiply the values, which feed the color too); a step of 0.01
on the slider (rejected: 0.05 gives 10 positions and the server accepts any number in the range).

## Decision 13 - Size between half and full, line width by age (added 2026-11-24)

**Decision**: `window_curves()` sizes every curve separately: its farthest point (`ext = val (5 + bc yval)` of the faded value,
the first point) is put `smallest_radius + (full_radius - smallest_radius) * min(1, ext * scale / full_radius)` pixels from
the center, `full_radius = min(w, h) / 2 - MARGIN - MAX_LINE_WIDTH`, `smallest_radius = min(min(w, h) / 4, full_radius)`; the
shape is the formula's, multiplied by `radius / ext`. `scale` is still `pixels_per_unit(file_extent)`, now computed with
`full_radius`, so `ext * scale / full_radius` is `ext / file extent`. The width is `entry_line_width(age, history)` =
`floor(5 - 4 age / (history - 1) + 0.5)`, at least 1; `window_curves` returns it as a third result `CurveWidths` `(curves,)`
(the new alias), and `_frame(curves, colors, width, height, widths=None)` gives each curve of the one `LineCollection` its own
width (`widths * 72 / 100` points).

**Rationale**: the user wants half of the smallest dimension as the least size and the full size as the most, and the pictures
were small most of the time. Reading "size" as the diameter makes the minimum an exact number (half the smallest side) and keeps
every curve in the room; the margin is kept, and the widest line is taken off the room so a 5-pixel line never touches the edge.
Using the extent (not the value alone) keeps a higher note bigger and the loudest curve of the file at the full size.

**Alternatives considered**: size by the value alone (rejected: it would ignore the index, which already widens the loops);
size as the radius (rejected: it would make the least curve the whole room's half, i.e. the diameter a quarter of the side);
line widths scaled with the picture's height as before (rejected: the user gave pixels, 5 to 1, as whole numbers);
`window_curves` returning two items and a second function for the widths (rejected: the widths must be dropped for the same
silent places as the curves).

## Decision 14 - The user's edits, turns and rc by the local peak, widths (added 2026-11-24)

**Decision**: the curve is `X = val (rc cos c1 + loops cos c2)`, `Y` with sines, `loops = (index mod 12) val`, `c2` from 0 to
`2 pi turns`, `turns = 2 * SMALL_TURNS * pct + MIN_TURNS` (6 to 20, not rounded) and `rc = RC` when `pct > 0.5`, else `RC - 1`;
`pct` is `spirograph.peak_percents(beat, frames)` = `1 - chromatic_decay.beat_distances(beat)`, one number for each frame
(`PeakPercents`; all 1 for `beat=None`), taken **per history entry** by `spiro_curves(values, indices, percents)`,
`file_extent(values, indices, percents)` and `window_curves(..., fade, percents)`. The extent of a curve is
`val (rc + (index mod 12) val)` (`_extents()`). The job measures the beat for Spirograph (`measure_local_peaks()` with the
Minimum distance of the request, `frame_positions()`), `write_frames` passes it on, and the page shows the Local peaks group
(`concentric-peaks`, Minimum distance) for Spirograph. `entry_line_width(age, history)` is 5 for age 0 and, for age 1 to
`history - 1`, `4 - 3 (age - 1) / (history - 2)` rounded half up, at least 1.

**Rationale**: the first part is the user's own change (`loops` by the modulo of the index, local `turns` and `rc`) turned
into functions of the beat, which the user asked for with `pctDistance`. The stretched beat is used because the raw position
of a frame inside real peaks stays above about 0.55 (research of feature 035), so the "closer to the peak" test of `rc` would
be always true and the turns would never fall below 14; the stretch makes the whole range from 0 to 1 occur, as it does for the
rings of Chromatic Decay. Per entry (not per picture) keeps a curve a function of its own entry only, so consecutive pictures
still share their entries. Not rounding the turns is the user's formula as written. The widths: the maximum is a constant 5 and
the first older entry is at most 4, so a thick line never lies at the same width as the newest one and does not hide the thin
ones; 4 to 1 over the rest keeps the old result for History 5 and 8.

**Alternatives considered**: the raw beat position as `pct` (rejected: see above); one `pct` for the whole picture (the
picture's own frame; rejected: an older entry would change shape from picture to picture); rounding `turns` to a whole number so
every curve closes (kept as a one-line option, not done: the user's formula has no rounding); `rc` 5 at exactly half way (the user
wrote "closer to the peak than to the minimum"; half way is neither); keeping the sizes by the old extent
`val (5 + bc yval)` (rejected: a curve would then pass the room, the farthest point is the new one); widths 5 down to 1 over
all the entries as before (rejected: History 9 or more repeated 5, which is the overlap the user saw).

*Update 2026-11-25: the user changed `MAX_LINE_WIDTH` to 3 (5 was still too thick). Decision 13's widths are now 3 for the newest entry and 2 down to 1 for the older (History 5: 3, 2, 2, 1, 1; 8: 3, 2, 2, 2, 2, 1, 1, 1; 12: 3, 2, 2, 2, 2, 2, 2, 1, 1, 1, 1, 1); the full radius follows (187 on 600 x 400). No other change.*
