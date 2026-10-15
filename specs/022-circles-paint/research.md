# Research: Circles Paint

No `[NEEDS CLARIFICATION]` remains (both questions were answered on 2026-10-14: the paint never fades or clears, and circles are solid). Facts about the code were read from the repository; the timings come from a prototype (`scratchpad/paint_proto.py`) for 1,800 random-but-music-like frames at 600 × 400, colormap inferno.

## What exists today

- `circles.py`: `plan_circles(values, peak, notes, unit, memory, width, height)` yields, for every frame, `(added, remembered)`: `added` is the list of the circles put down in the frame, weakest first, each `(x, y, color index)` with the place worked out from the rank's previous place, the note's angle and distance (scaled by `width / 252`), the stay-in-place rule and the wrap; `remembered` is the last `memory` circles. `write_circle_frames` draws every remembered circle onto a four times larger canvas with a fill whose alpha falls with the circle's age, and averages the canvas down.
- `resize_factor(color, resize)`, `check_circle_*`, `MIDDLE_COLOR_ROW`, `SUPERSAMPLE`, `REFERENCE_WIDTH` are all there.
- `frame_rendering.write_frames` has one `if image_type == "circles":` branch that returns before the grid pipeline, checks every circle setting for every type, and passes the sizes.
- `IMAGE_TYPES = ("tiles", "blended", "contour", "circles")`; `check_image_type` builds its message from the tuple, so the refusal message and the tests that derive from the tuple follow it.
- Frontend: `IMAGE_TYPES` (value, label), `gridSettingsApply(imageType)` (false for circles), the group model `groups.ts` (a group per type, ids equal to the image type values), `App.vue`'s summary (`result.image_type === 'circles'` for the circle lines), `SettingsForm.vue` (`TYPE_GROUP_IDS`).

## Decision 1: The type is `circles_paint`, labelled "Circles paint"

- **Decision**: The request value and the group id are `circles_paint`; the label on the page is "Circles paint". The tuple becomes `("tiles", "blended", "contour", "circles", "circles_paint")`.
- **Rationale**: Image type values are lowercase single names; the underscore reads as the two words of the label and cannot be confused with `circles`. The refusal message lists five names automatically.
- **Alternatives considered**: `paint` or `circlespaint` (less clear or less readable); a setting of Circles (the spec says a type of its own, so both can be chosen and their settings differ).

## Decision 2: Reuse `plan_circles`, with `memory=None` for "no memory"

- **Decision**: `plan_circles` accepts `memory=None`: no check of the memory, a buffer that keeps nothing (`deque(maxlen=0)`), so `remembered` is empty and `added` is exactly what it was. The paint writer reads only `added`.
- **Rationale**: FR-003 and SC-003 ("the circles are exactly those of Circles") hold by construction, not by a copy of the rules; there is no memory to build (and no per-frame copy of 300 circles).
- **Alternatives considered**: pass the default memory and ignore it (works, but builds and copies a list of up to 500 circles per frame for nothing); a second planning function (a copy of the rules that could drift).

## Decision 3: Paint each circle through a small coverage mask

- **Decision**: For a circle of center `(x, y)` and radius `r` (the radius setting times `width / 252` times the resize factor): take the whole-pixel box `floor(x - r) - 1 .. ceil(x + r) + 1` (and the same for y); draw the disc on an `L` patch of that box four times larger (`SUPERSAMPLE`), with the same boundary arithmetic as the circles writer (the far end of the box minus one); average the patch down (`reduce`) to a coverage mask of 0 to 255; clip the box to the canvas (the circle is cut off by the edge, not painted again on the opposite side, as in Circles); `canvas.paste(color, box, mask)`.
- **Rationale**: The interior has coverage 255 so a pixel well inside is exactly the circle's color (SC-004a), the edge pixels are the mix of the color and what is there (smooth edges as in Circles, same geometry and supersampling), and the work per circle is the size of its own patch (at most about 116 × 116 pixels, four times that on the patch), not of the 600 × 400 frame.
- **Alternatives considered**: draw the circle onto a four times larger copy of the whole canvas (2,400 × 1,600 per frame: what the memory version does, and the canvas would have to be kept at that size or re-enlarged each frame, losing detail); `ImageDraw.ellipse` straight on the canvas (hard, stair-stepped edges; the user asked for smoothness earlier).
- **Prototype result**: 4.4 s for the default settings and 2.5 s for the largest (12 circles of radius up to 57 pixels per frame), 1,800 frames each.

## Decision 4: The canvas persists; each frame saves a copy

- **Decision**: One `RGB` canvas of the frame size is created with the background color (the colormap's middle color, row 128). After the circles of a frame are painted, `canvas.copy()` is submitted to the saving threads (the same few-thread pool as Circles); the canvas itself goes on to the next frame. A frame with no circle saves a copy of the unchanged canvas.
- **Rationale**: FR-005 and SC-002/SC-005 (a frame is the previous one with the circles on top; silent frames are exact copies). The copy is needed because the saving runs on other threads while the main thread paints the next frame (a copy is 720 KB).
- **Alternatives considered**: save on the main thread (slower, the PNG encoding is the larger part of the cost); read each previous frame back from its file (lossless PNG, but slower and pointless).

## Decision 5: Settings: Memory is validated and ignored

- **Decision**: The request fields are those of Circles (`circle_unit`, `circle_radius`, `circle_resize`, `circle_notes`, and `circle_memory`). `circle_memory` is still checked (a value that is not allowed is refused for every image type, as every circle setting is today) and is then ignored by this type; the response reports it as for the other types. The writer's signature has no `memory`.
- **Rationale**: The spec's FR-008 and its edge case ("accepted and ignored"); the page does not show Memory for this type, so it is the default unless a client sends another.
- **Alternatives considered**: not checking `circle_memory` for the new type (a different rule for one type; the current rule is "validated whatever the image type").

## Decision 6: Frontend: one more group, one helper

- **Decision**: `validation.ts` gets `{ value: "circles_paint", label: "Circles paint" }` after Circles and `isCirclesType(imageType)` (true for both); `gridSettingsApply` becomes `!isCirclesType(imageType)`. `groups.ts` gets the group `circles_paint` titled "Circles paint" with `circle-unit`, `circle-radius`, `circle-resize`, `circle-notes` (that order, so two rows of two), and `TYPE_GROUPS` and the form's `TYPE_GROUP_IDS` list it. The form needs no other change: it shows a control when `controlsIn(typeGroup)` has it, so Memory is simply not there, and the values of all controls stay in the form's refs, so switching between Circles and Circles paint keeps Movement, Radius, Resize and Notes and Circles gets its Memory back. `App.vue` shows the circle lines for either circle type and the Memory line for `circles` only.
- **Rationale**: Minimal change on top of the group model of feature 020; the five-name refusal message, the image type dropdown and the summary follow.

## Decision 7: Image type help text

- **Decision**: `imageTypeHelp` gets a sentence: Circles paint makes the same circles but keeps no memory: each frame is the previous picture with the new circles painted on it, solid, and nothing fades.

## Decision 8: Tests

- **Decision**: `test_circles_paint.py`, written first: (a) the plan with `memory=None` adds exactly the circles that the plan with a memory adds, frame by frame, for random values and for every setting (and does not keep a memory); (b) the canvas: the first frame is the background plus its circles; for every later frame every pixel outside the (clipped) boxes of that frame's circles equals the same pixel of the previous frame, exactly; silent frames are exact copies; two runs are identical; (c) the circles: the pixel at the center has exactly the colormap's color (for every colormap, whatever was painted before), the pixel just inside the radius too, the strongest on top where circles overlap, a ring of in-between colors on the edge (mix of the color and what was under it), a circle near an edge is cut off and nothing appears on the opposite side, the scaling to 600 × 400 (radius and step times 600 / 252); (d) no memory: after more circles than Circles' largest memory (500) have been painted, the first circle is still there where nothing covered it; (e) the circles are those of Circles: `added` equal, and the center pixel color of Circles' newest circle (opaque) equals the paint's; (f) refusals and ignoring: bad settings refused for the type as for the others, `circle_memory` accepted and without effect (frames equal with and without it); (g) the API: the type is accepted, every frame is 600 × 400 RGB, the response reports the type, the five names in the refusal message; (h) the other types' reference hashes.
- **Rationale**: Each acceptance scenario and success criterion of the spec has a test; mutation checks follow the work.

## Decision 9: Time and room

- **Prototype results** (1,800 frames of 600 × 400; time and the room of the PNG files):

| Settings | Circles paint | Circles |
|----------|---------------|---------|
| defaults (8 notes, movement 4, radius 4, memory 300) | 4.4 s, 332 MB | 17.3 s, 113 MB |
| largest (12 notes, movement 10, radius 8, resize on, memory 500) | 2.5 s, 78 MB | 175.8 s, 130 MB |

- **Decision**: No tuning is needed to meet SC-006 (one minute, and no slower than Circles). The room is larger than Circles' at the default settings (2.9 times): the canvas keeps all its detail, so its PNGs are large; at the largest settings the big solid circles cover the canvas and the files are small. The spec asks only that the room be of the same order; if it ever matters, a higher PNG compression level for this type is the first thing to try.
- **Note**: the 176 s of Circles above is with Resize by volume on at the largest settings (circles up to three times the radius, their area nine times): it is above the two-minute limit that feature 021 set, whose own measurement had the resize off. That is outside this feature and is reported, not fixed.

## Decision 10: Documentation

- **Decision**: README gets the fifth image type in the Image type paragraph and a Circles paint paragraph after Circles; the documents of features 019 and 020 that count four image types get an amendment note.

## Open items

None. Not verifiable here: how the canvas looks as it builds up in the player in a real browser, and whether a long file's dense layering is pleasing (a matter of taste; the spec says it is expected).
