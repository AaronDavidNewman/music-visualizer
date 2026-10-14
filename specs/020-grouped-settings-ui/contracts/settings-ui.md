# Contract: The settings form and the radius field

The change to the settings page and, for the radius, to the job endpoint. Everything not listed here is as in the earlier contracts.

## The settings page

### Structure

- The form is a vertical list of **groups**, in the order of `data-model.md`: Analysis, Colormap, Image type, the group of the chosen type (Tiles, Contour, Blended Tiles or Circles), Data smoothing, Image smoothing (not for Circles), then the **Create frames** button.
- A group is a `<details>` element whose `<summary>` is its title. It is open when the page loads. Activating the summary (click, Enter or Space) toggles it; the toggle of one group does not touch another.
- The summary shows, besides the title, a visible text mark "needs attention" when any control of the group has an invalid value (the mark is text, not colour alone).
- The body of a group is a flex container that wraps; each control is a **cell** holding its label (with the info button), its input and its error or notice. **Two cells to a row**; the last cell of an odd group fills its row. On a viewport narrower than about 26 rem every cell fills its row.
- A control that has no meaning for the chosen image type is **not rendered**. Its value is kept and still sent with the request.
- Slider cells show the readout in the label row, right-aligned (for example `4 px`, `300 circles`, `1 (every frame drawn)`).

### Names

| Place | Shows |
|-------|-------|
| form labels, info buttons (`aria-label` "About ..."), info texts | Movement, Radius, Resize by volume, Memory, Notes (circles), Oversampling |
| validation messages under the controls | `The circle movement must be a whole number from 1 to 10.`, `The circle radius must be a whole number from 4 to 8.`, `The oversampling must be a whole number from 1 to 5.` (the others unchanged) |
| result summary | Movement, Radius, Resize by volume, Memory, Notes, Oversampling |

No place shows Unit, Size, Circles per frame or Resolution.

### Controls (ids) per type

| Image type | Group 4 title | Control ids in it |
|------------|---------------|-------------------|
| Tiles | Tiles | `threshold`, `notes` |
| Contour | Contour | `threshold`, `notes` |
| Blended tiles | Blended Tiles | `threshold`, `notes`, `blend-width` |
| Circles | Circles | `circle-unit`, `circle-radius`, `circle-resize`, `circle-memory`, `circle-notes` |

`resolution` and `interpolate` are in Image smoothing for the three grid types and absent for Circles. `smoothing-window` and `smoothing` are in Data smoothing for every type. `window-size`, `frame-rate` and `window-spacing` are in Analysis; `colormap` and `image-type` have a group each.

### Accessibility

- The expanded or collapsed state of a group is exposed by the `<details>` element itself.
- Labels stay tied to their inputs (`for` / `id`); the info buttons keep their `aria-label`.

## `POST /api/jobs`: the radius

| Field | Type | Default | Rule |
|-------|------|---------|------|
| `circle_radius` | text | `4` | A whole number from 4 to 8 (`4` and `4.0` accepted). Empty, not a number, fractional, out of range or not finite: refused. Validated whatever the image type is. |
| `circle_size` | - | - | **Removed.** A request that still sends it is accepted and the field is ignored (like every unknown form field). |

Refusal: HTTP 400, before any audio is read or job created:

```json
{ "detail": "The circle radius must be a whole number from 4 to 8." }
```

Changed messages (same rule as before, new wording):

```json
{ "detail": "The circle movement must be a whole number from 1 to 10." }
{ "detail": "The oversampling must be a whole number from 1 to 5." }
```

Success response (200): `circle_radius` replaces `circle_size`:

```json
{ "image_type": "circles", "circle_unit": 4, "circle_radius": 4, "circle_resize": false, "circle_memory": 300, "circle_notes": 8 }
```

The frames: for `circles` a disc has the radius `circle_radius` (times `1 + 2 c / 255` with Resize by volume on). Placement, colors, opacities, fading and smoothing of the edges are unchanged. The other image types are byte-identical to before.
