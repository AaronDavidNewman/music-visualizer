# Contract changes: HTTP API

Changes to `POST /api/jobs` from [feature 002](../../002-audio-frames-ui/contracts/http-api.md) and [feature 003](../../003-window-spacing/contracts/http-api-changes.md). Everything not listed is unchanged, including the frame endpoint.

## Request: new field

| Field | Type | Notes |
|-------|------|-------|
| `brightness` | text, optional | A whole number from 2 to 100. Leave the field out to use 2. |

## Response: new field

```json
{
  "brightness": 4
}
```

| Field | Meaning |
|-------|---------|
| `brightness` | The brightness used. 2 when the request had no `brightness` field. |

## New error

| Status | When | `detail` |
|--------|------|----------|
| 400 | `brightness` is present but is not a whole number from 2 to 100 (including an empty value, a decimal, text, `nan`, `inf`, 1 and 101) | "The brightness must be a whole number from 2 to 100." |

It is returned with the other parameter errors, before the file is stored, so a refused request leaves nothing behind. A missing field is not an error.

## Image content contract (replaces the gray level rule in feature 002)

- Square gray level is `round(255 × (level / 255)^(1 / brightness))`, where `level = round(255 × value / file_max)`. Since feature 007 this gray level is the tile's HSV value, so it is the brightest channel of the tile's color (the tiles are colored; the brightness setting still sets how bright they are).
- With brightness 2 this is the square-root boost used before this feature, and the images are identical to those.
- 0 stays 0 and 255 stays 255 at every brightness. A higher brightness is never darker.

## UI contract additions

| Element | Behavior |
|---------|----------|
| Brightness field | A number input, whole numbers 2 to 100, default 2, showing the range. Disabled while a submission runs. Keeps its value after errors and completed submissions. |
| Hint | "Higher values lift quiet notes more but show less contrast." |
| Validation | Blocks submission with "The brightness must be a whole number from 2 to 100." for an empty value, a decimal, text, or a number outside the range. |
| Results summary | Adds the brightness used. |
