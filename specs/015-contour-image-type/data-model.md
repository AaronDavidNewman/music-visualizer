# Data Model: Contour Image Type

No stored data is added. These are the values that exist while a job is created, and the rules between them. The notation `S` is the smoothed note array of the whole file, shape `(frames, 88)`.

## Image type

| | |
|-|-|
| Values | `tiles` (default), `blended`, `contour` (lowercase, exact) |
| Where it lives | `IMAGE_TYPES` and `DEFAULT_IMAGE_TYPE` in `backend/app/services/image_types.py`; `IMAGE_TYPES` (value and label) in `frontend/src/utilities/validation.ts` |
| Refusal | any other value, including an empty one: `The image type must be one of tiles, blended, contour.` (built from the tuple) |
| Labels on the page | Tiles, Blended tiles, Contour |
| Effect of Blend width | none for `tiles` and `contour`; used by `blended` only |

## Contour inputs of one job

| Name | Definition |
|------|------------|
| `peak` | `S.max()` over all 88 notes of the whole file, after smoothing; 0 for a silent file |
| `hidden` | `hidden_notes(S, threshold)`, shape `(frames, 84)`, unchanged from feature 011 |
| `values` | `S[:, :84]` with `values[hidden] = 0` |
| `Z[t]` | `values[t].reshape(7, 12)`, so note `n` is at row `n // 12`, column `n % 12`; drawn as `Z[t][::-1]` so that row 0 (the lowest octave) is at the top of the picture |
| `top[t]` | `values[t].max()`, the largest value of frame `t` (the drawn notes, hidden ones as 0); worked out again for every frame |
| `X`, `Y` | `np.linspace(0, top[t], 12)` and `np.linspace(0, top[t], 7)`, per frame. With the axes off and X and Y scaled together this changes no pixel; the color scale below is what fixes the colors |
| Color scale | `vmin = 0`, `vmax = top[t]`, the frame's own largest value (changed by the user on 2026-10-12; it was `peak`, the same for every frame); linear in the value |
| Levels | chosen by matplotlib for each frame; not stored and not known to the application |
| Colormap | the job's colormap name, used as matplotlib's `cmap` |

## Rules

- A frame in which `Z` has the same value everywhere (including all zero, and every frame when `peak` is 0) is a **flat picture** of one color: the colormap's color at `value / peak` on the scale, the first color for 0. It is made with Pillow, not `contourf`. (A frame with all notes hidden is such a frame.)
- Otherwise the frame is `contourf(X, Y, Z[::-1], cmap=colormap, vmin=0, vmax=top[t])` on an axes that fills a 252 × 168 pixel figure with the axis decorations off, saved by `pyplot.savefig` as `frame_NNNNNN.png`.
- The frame count, the file names and the timing are the same as for the other types (FR-011): the file name is `frame_` plus the six-digit index.
- Smoothing (`smooth_frames`), its window and the threshold (`hidden_notes`) are the existing functions, called before the choice of the image type, with the same arguments, so the notes that are hidden are the same in every type.
- The drawing of a job holds one process-wide lock (the `pyplot` state is global).

## Response

No new field. `image_type` reports `contour`; `blend_width` is reported as always (the value sent or the default) and has no effect.
