# Contract: The note layout (API, library and UI)

The change to the job endpoint, the library functions and the settings page. Everything not listed here is as in the earlier contracts.

## `POST /api/jobs`

A new optional field.

| Field | Rule |
|-------|------|
| `note_layout` | Exactly `rows` or `spiral` (lowercase, no spaces); default `rows`. Anything else, including empty: HTTP 400 `The note layout must be one of rows, spiral.` (before any audio is read, nothing created). |

Effect: for `image_type` `tiles`, `blended` or `concentric` the 84 notes are drawn in the cells of the chosen layout (data-model.md); for `contour`, `circles` and `circles_paint` the value is checked and has no effect. With `rows` (or not sent) the frames are byte-identical to those made before this feature.

The response adds `note_layout` (the value sent or its default), for every image type.

## The frames

- Rows: unchanged.
- Spiral, Tiles and Blended tiles: the tile of note `n` is the tile of the cell where the table puts `n`, with the color, hiding and fade it would have in the rows layout; Oversampling blends the tiles that are next to each other on the screen; the notes kept by Notes are spread in pitch order along the spiral.
- Spiral, Concentric: the circle of note `n` is centered on the cell of `n` with the radius and rings it would have in the rows layout.
- Sizes, counts, names and timing are those of the other layouts.

## Library

```python
# app/services/note_layout.py
LAYOUTS = ("rows", "spiral"); DEFAULT_NOTE_LAYOUT = "rows"
check_note_layout(value) -> str                 # ValueError("The note layout must be one of rows, spiral.")
note_order(layout) -> int array (84,)           # the note drawn in each cell, row by row
arrange_notes(values, layout) -> float array (frames, 84)   # values in cell order; the input is not changed

# app/services/frame_rendering.py
write_frames(..., beat=None, note_layout="rows")
```

## The settings page

- A group "Note layout" with one dropdown (Rows, Spiral; Rows selected at the start), shown for Tiles, Blended tiles and Concentric, after the group of the image type (after Image type for Concentric) and before Local peaks; not shown for the other types.
- The value is kept when the group is folded or the type is changed and is always sent.
- The result summary shows "Note layout: Rows" or "Spiral" for those three types.
