# Contract: Colormap (API and UI)

The change to the server's job endpoint and to the settings page. Everything not listed here is as in the earlier contracts.

## `POST /api/jobs`

One new optional multipart form field:

| Field | Type | Default | Rule |
|-------|------|---------|------|
| `colormap` | text | `hot` | Exactly `summer`, `autumn`, `hot` or `cool` (lowercase, no spaces). Not sent: `hot`. Sent but empty or anything else (`Hot`, ` hot`, `viridis`, `hot_r`): refused. |

Refusal: HTTP 400, before any audio is read or any job is created:

```json
{ "detail": "The colormap must be one of summer, autumn, hot, cool." }
```

**Removed fields.** `energy`, `brightness`, `hue_step`, `saturation_step` and `brightness_step` are no longer part of the endpoint. A request that still sends them is accepted (no 400) and the values have no effect: the frames are identical to those of the same request without them.

The remaining fields are unchanged: `file`, `window_size`, `frame_rate`, `window_spacing`, `smoothing`, `smoothing_window`, `threshold`, `image_type`, `blend_width`.

Success response (200): the fields `brightness`, `energy`, `hue_step`, `saturation_step` and `brightness_step` are gone and one field is added, the colormap used:

```json
{ "colormap": "hot" }
```

All other response fields are unchanged: `job_id`, `file_name`, `sample_rate`, `duration_seconds`, `window_size`, `frame_rate`, `frame_count`, `smoothing`, `smoothing_window`, `threshold`, `image_type`, `blend_width`, `window_spacing`, `step_samples`, `window_count`, `spacing_raised`, `frame_url_template`.

## Frames

`GET /api/jobs/{job_id}/frames/{index}` is unchanged in URL, media type (`image/png`), cache header, size (252 × 168 pixels) and, per image type, file format.

Each drawn tile's color is the color of the chosen matplotlib colormap at a position worked out from that tile's own note strength only (see [data-model.md](../data-model.md)): the smoothed note value as a share of the largest smoothed note value in the file, square-rooted, rounded to one of 256 table entries. A note hidden by the threshold is black. The color does not depend on any other note, on the loudness of the frame or on the frame's number, so a steady note has a steady color. A silent file has every tile in the colormap's first color. Frames for the same file and settings are identical on every request.

## Settings page

- A **Colormap** dropdown directly after the window size / frame rate / window spacing row, offering **Summer**, **Autumn**, **Hot** and **Cool** (values `summer`, `autumn`, `hot`, `cool`), starting at Hot, with an info button (accessible name "About colormap") that says what each scale looks like and that the same strength always gets the same color. Disabled while a job is running.
- The controls **Brightness**, **Saturation**, **Hue steps**, **Saturation steps** and **Brightness steps** are removed. The remaining controls are unchanged: Window size, Frame rate, Window spacing, Smoothing window, Smoothing, Threshold, Image type and Blend width.
- The form sends `colormap` and no longer sends the removed fields.
- The result summary has a new item `Colormap: Hot` (the label of the colormap used) and no longer shows `Brightness`, `Saturation`, `Hue steps`, `Saturation steps` or `Brightness steps`.
