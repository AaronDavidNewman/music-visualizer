# Research: Contour Image Type

No `NEEDS CLARIFICATION` items remain in the spec. The method (matplotlib `contourf`, `np.linspace` coordinates, a 0-to-`max` color scale, the selected colormap, axes off, `pyplot.savefig`) was given by the user, and on 2026-10-11 they asked for the contour levels to be left to matplotlib. The decisions below were checked with a throwaway prototype (matplotlib 3.10.9, Agg backend, a synthetic 300-frame file of 84 notes), not assumed.

## Measurements from the prototype

| Question | Result |
|----------|--------|
| Import cost of `matplotlib.pyplot` with the Agg backend | about 0.24 s, paid on the first contour job only |
| Time per frame (`ax.clear()`, `contourf`, `pyplot.savefig`), one figure reused | 8.3 ms; 300 frames in 2.5 s |
| Time per frame with a new figure for every frame | 9.8 ms |
| Size and mode of the saved PNG | exactly 252 × 168, RGBA, all pixels opaque, about 1.4 KB |
| Pixels equal to white, and alpha below 255, with the axes filling the figure | none; the picture is covered edge to edge |
| Same data twice, in two different figures | byte-identical files |
| Levels chosen by matplotlib | multiples of a "nice" step that cover the frame's range, for example `0, 0.15 ... 1.05` in one frame and `0, 0.1 ... 0.7` in another (so the number of bands differs from frame to frame) |
| A frame whose values are all the same (all 0, or one constant) | no error and no warning, but matplotlib draws a degenerate picture (a few hundred black pixels among slightly different shades of one color) |
| Largest difference between a grid point's pixel and the colormap's exact color for the note's value | 53 of 255 on one channel for `hot`, which is a band's width, as expected |
| Figures left open after `pyplot.close` | none |

## Decision 1: Draw with `pyplot` on the Agg backend, one figure per job, behind a lock

- **Decision**: A new module `app/services/contour.py` imports `matplotlib`, selects the `Agg` backend with `matplotlib.use("Agg")`, then imports `matplotlib.pyplot`, all inside the function that draws, so nothing is imported at server start or by a tiles or blended job. For a job it opens one figure of 2.52 × 1.68 inches at 100 dots per inch (`IMAGE_WIDTH / 100` by `IMAGE_HEIGHT / 100`, which `savefig` turns into exactly 252 × 168 pixels), adds one axes that fills the figure (`pyplot.axes([0, 0, 1, 1])`), and for every frame clears the axes, switches the axis decorations off with `set_axis_off()`, calls `contourf` and saves with `pyplot.savefig(path)`. The figure is closed in a `finally`. The whole drawing of a job runs under one module-level `threading.Lock`.
- **Rationale**: This is the user's method (`contourf`, `set_axis_off`, `pyplot.savefig`). `pyplot` keeps global state (the current figure and axes), and the job endpoint is a plain `def`, which FastAPI runs on a thread pool, so two simultaneous contour jobs would otherwise draw into each other's figure; the lock makes that impossible, and contour jobs are short (seconds), so serializing them costs little. Reusing one figure saves creating 300 figures and measures slightly faster. Agg is required on a server and opens no window.
- **Alternatives considered**: The object-oriented `Figure` and `FigureCanvasAgg` classes with `fig.savefig`: no global state and no lock, but not what the user named. The user can ask for it later; the change would be local to `contour.py`. A new figure per frame: simpler but 18% slower. Drawing the frames in parallel in several threads or processes: not needed at 8 ms a frame (SC-007 asks for 60 s for 300 frames and the measurement is 2.5 s), and `pyplot` is not thread-safe.

## Decision 2: The color scale is fixed with `vmin` and `vmax`; the levels are matplotlib's

- **Decision**: `contourf(x, y, z, cmap=colormap, vmin=0, vmax=peak)` with no `levels` argument. `peak` is the largest smoothed value of the whole file over all 88 notes. `vmin` and `vmax` fix the normalization of colors, so a given value has the same position on the colormap in every frame, while matplotlib chooses the levels for the data of each frame by itself. Nothing in the code or the tests names a number of levels.
- **Rationale**: Without `vmin` and `vmax`, `contourf` scales the colors to each frame's own range, which would make quiet frames as bright as loud ones. With them the scale is the specified 0 to `max`. Leaving `levels` out is the user's clarification. The prototype shows the colors stay on the fixed scale while the levels change from frame to frame.
- **Alternatives considered**: Passing `levels=np.linspace(0, peak, n)`: reproducible bands, but it hard-codes `n`, which the user declined for now. Normalizing with `matplotlib.colors.Normalize(0, peak)`: the same effect as `vmin` and `vmax`.
- **Note on the scale**: The tiles pictures take the square root of the strength before looking up the color (feature 014). The user's description of the contour says the scale runs from 0 to the maximum value and the Z values are "just the smoothed note values", so the contour's scale is **linear**. This is a visible difference between the types (a quiet note is closer to the start of the colormap in a contour than in tiles); it is documented in the README and can be changed later by passing `np.sqrt(z / peak)` and a 0-to-1 scale, a one-line change.

## Decision 3: The grid, the orientation and hidden notes

- **Decision**: `x = np.linspace(0, top, 12)`, `y = np.linspace(0, top, 7)`, where `top` is the largest value of the frame being drawn (recomputed for every frame; the user's request of 2026-10-11, after the first implementation used the file's peak; measured on 40 random frames: no pixel differs between the two, because X and Y scale together and the axes are not shown); `z` is the `(7, 12)` array of the drawn notes' smoothed values (`smoothed[:, :84].reshape(7, 12)`, so note `n` is at row `n // 12`, column `n % 12`, as in the tiles), flipped top to bottom (`z[::-1]`) before drawing, because `contourf` puts the first row at the bottom and the tiles put the lowest octave at the top. Notes hidden by the threshold (`hidden_notes`, unchanged) are set to 0 in `z`. The smoothing, its window and the threshold are applied before, exactly as for the other types, by the same functions.
- **Rationale**: The same note stays in the same place in every image type (FR-006). Flipping the data is simpler and cheaper than inverting the axis, and the coordinates are only proportions because the axes are not shown.
- **Alternatives considered**: `ax.invert_yaxis()`: equal result, one more call per frame. Leaving matplotlib's orientation: the contour would be upside down relative to the tiles.

## Decision 4: Frames with nothing to contour are drawn as one flat color

- **Decision**: If a frame's `z` has the same value everywhere (every value 0 in a quiet frame, a silent file, or all notes hidden; the equal-nonzero case is the same code path) the picture is a flat image of one color and `contourf` is not called. The color is the colormap at that value on the 0-to-`peak` scale, which for 0 is the colormap's first color (`lookup_table(name)[0]`, the same first color as the other image types give a silent file). The flat picture is written as an RGB PNG of the same size with Pillow. When `peak` is 0 the file is silent and every frame is such a picture.
- **Rationale**: The prototype shows `contourf` makes a degenerate picture for constant data (black specks), and with `peak = 0` the scale `vmin = vmax = 0` is meaningless. A flat picture is what the spec requires (FR-008, SC-006) and is cheaper to make.
- **Alternatives considered**: Calling `contourf` with an explicit two-level list for constant data: still draws through matplotlib and needs a special case anyway. Letting matplotlib draw it: wrong output, as measured.

## Decision 5: A third name in the image type list, nothing else in the existing path

- **Decision**: `IMAGE_TYPES = ("tiles", "blended", "contour")` in `image_types.py`; the refusal message, the router's `_parse_image_type` and the response follow from the tuple. `write_frames` gets one new branch: for `contour` it takes the smoothed values and the hidden mask, and hands them to `contour.write_contour_frames`; the tile colors (`colorize`) are not needed for it. The tiles and blended branches are not edited, so their files cannot change (FR-002, checked with the reference hash of the default output recorded in feature 014: `28e60886…d780`). The blend width is accepted and ignored for contour, as it is for tiles.
- **Rationale**: The router already validates by the tuple, so the server side is almost free. Keeping the new drawing in its own module keeps `frame_rendering.py` free of matplotlib's drawing (it stays a lazy import in two modules).
- **Alternatives considered**: Putting the drawing in `image_types.py`: that module is pure numpy by design. Making the writers a registry keyed by the image type name: reasonable when a fourth type arrives, not worth a refactor of working code now.

## Decision 6: The page

- **Decision**: `IMAGE_TYPES` in `validation.ts` gains `{ value: "contour", label: "Contour" }`. The Blend width slider's disabled condition changes from "image type is tiles" to "image type is not blended" (the spec requires it to be disabled for Contour as well). `imageTypeHelp` describes Contour in one more sentence. The result summary already shows the blend width only for `blended`; it shows "Contour" through `imageTypeLabel`. `api.ts` comments mention the third value.
- **Rationale**: The dropdown is built from the list, so the choice appears by adding one entry. Switching the slider rule to "not blended" also keeps it correct for any later type.
- **Alternatives considered**: Hiding the slider for Contour: the spec says disabled, as for Tiles.

## Decision 7: Tests do not depend on a number of levels or on particular colormaps

- **Decision**: The contour tests use `DEFAULT_COLORMAP`, `COLORMAPS`, `FIRST`, `SECOND` and the other helpers from `backend/tests/colormap_names.py` (feature 014's list-tolerant tests), and none of them states a number of levels. What they check, for every offered colormap: size 252 × 168; every pixel opaque and the pixels along the four edges are not the figure's background; a pixel at a note's grid point has a color that the colormap has somewhere within one band of the note's position on the 0-to-`peak` scale (tested as "equal, within 1 per channel, to the colormap's color at some position within 0.25 of the value's position", which holds for any number of bands up to four and for cyclic maps such as `hsv`); the strongest note's area is at the far end of the scale for a file with a single peak and the zeros at the start; the same strength has the same color in different frames of one file; hidden notes lower the picture exactly as a 0 would (the frame equals the frame in which the note's value is really 0); a silent file and a frame of all zeros are uniform in the colormap's first color; tiles and blended files are byte-identical to the reference; two runs are byte-identical; 300 frames finish inside the SC-007 bound; two simultaneous contour jobs both come out right (the lock). Orientation is tested with one loud note in the top-left and one in the bottom-right of the grid.
- **Rationale**: The user will change the colormap list by hand and wants matplotlib, not the code, to choose the levels. A test that counted bands or compared to a hard-coded level list would break the first time either changes.
- **Alternatives considered**: Recomputing matplotlib's own contour in the test and comparing pixels: it would only restate the implementation.

## Decision 8: Dependency and environment

- **Decision**: No new dependency: matplotlib (with its Pillow, numpy and contourpy) is already in `requirements.txt` since feature 014. No change to `requirements-dev.txt`.
- **Rationale**: `pyplot` and `contourf` are part of the package that is already installed (3.10.9).
- **Alternatives considered**: None needed.
