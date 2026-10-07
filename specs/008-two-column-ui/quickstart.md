# Quickstart: Two-Column UI

Validation guide for [spec.md](spec.md). The page layout and popover behavior are in [contracts/ui-layout.md](contracts/ui-layout.md), and the state and settings are in [data-model.md](data-model.md).

## Prerequisites

Same as the earlier features (`pip install -r requirements-dev.txt` in `backend/` with the venv active, `npm install` in `frontend/`). A short `.wav` file to upload.

## 1. Automated checks

```
cd frontend
npm test
npm run typecheck
npm run build

cd ..\backend
pytest -v
```

Expected: everything passes. New coverage: popover placement (below, flipped above, clamped at the left, right, top and bottom edges, a popover larger than the viewport) and the explanation text for each setting, including the spacing text with and without a valid value. The backend has no change.

## 2. Run the application

```
cd backend
uvicorn app.main:app --reload       # http://localhost:8000

cd frontend
npm run dev                         # http://localhost:5173
```

Open http://localhost:5173 at a window about 1280 px wide.

## 3. Check each story

**Story 1: two columns**

1. The file chooser is at the top of the left column and the settings and "Create frames" are in the right column. No preview is shown yet.
2. Choose a `.wav` file, then create frames. While it runs, the progress message appears in the left column.
3. The summary, preview, play/pause, loop, time, frame position and slider appear under the chooser in the left column. The settings stay in place on the right.
4. Without scrolling (1280 px wide), change brightness and create frames again. The new preview shows in the left column.
5. Upload something that fails (for example, a non-WAV renamed to `.wav`). The error appears in the left column.

**Story 2: one row**

1. Window size, frame rate and window spacing are on one row, each with its label.
2. Clear the frame rate. Its error appears under it, the other two keep their values, and "Create frames" is disabled.
3. Change the window size. The spacing default updates as before. Set the spacing very low and confirm the below-minimum notice appears under the spacing field.

**Story 3: info popovers**

1. No explanatory sentence is printed under any field. Each setting has an info button.
2. Click an info button. A popover with the explanation opens beside it. Escape closes it. Open it again and click elsewhere, then click the button twice. Each closes it.
3. Open one popover and then another. Only the second stays open.
4. With the keyboard alone, Tab to an info button, press Enter or Space to open it and Escape to close it. With a screen reader (or the browser's accessibility tree), the button is named "About window size" and reports expanded/collapsed.
5. Open the popover of the spacing field with a valid value and confirm it shows the step between windows. Enter an invalid frame rate and confirm the error is still shown inline.
6. While a job runs, confirm the info buttons still open popovers although the settings are disabled.
7. Open a popover for the rightmost control near the window's right edge, and again at a narrow width. It stays fully visible.

**Story 4: narrow window**

1. Narrow the window to 360 px. The columns stack with the file chooser and preview first and the settings after.
2. The row of three wraps onto more lines. No horizontal scrollbar appears. Popovers still open and stay on screen.

## 4. Adding a setting does not move the preview (SC-005)

Temporarily add several dummy fields to `SettingsForm` and confirm the preview's position and size do not change. Remove them afterward.

## 5. Same output as before (SC-008)

Create frames with the same file and settings on this branch and on `main`. The frame count, summary text and a few downloaded frames are identical.
