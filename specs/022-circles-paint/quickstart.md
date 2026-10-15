# Quickstart: Validating Circles paint

Prerequisites: the repository as it is, the backend `.venv`, `npm install` done in `frontend/`. If the backend suite fails only at `test_the_frontends_list_matches_this_one_name_for_name_in_the_same_order` (or at import because the default colormap is not in the user's list), that is the user's colormap edit, not this feature; earlier features were verified with a temporary default (`scratchpad/run_with_default.py`).

## 1. Automatic checks

```text
cd backend && .venv\Scripts\python -m pytest -q
cd frontend && npx vitest run && npx vue-tsc --noEmit && npm run build
```

Expected: everything passes. New coverage includes: the plan reused with no memory (the same circles as Circles, frame by frame); the canvas (the first frame, every pixel outside a frame's circles equal to the previous frame's, silent frames as exact copies, determinism); solid circles of exactly the colormap's color inside and a mix on the edge; the strongest on top; circles cut off at the edges and not wrapped in the picture; the scaling to 600 × 400; no memory (the first circles survive more circles than Circles could remember); the API (the type, 600 × 400 RGB frames, the five names in the refusal); the page's group and summary.

## 2. The other image types did not change

```text
cd backend && .venv\Scripts\python <scratchpad>\hashes019.py
```

Expected: the four reference hashes of tiles, blended, Blues/smoothing/threshold and contour equal those recorded for feature 021 (`6819990556fd4095`, `f32a99c59fcb87fc`, `92b3a27dee73e223`, `dff443e80f5eed3f`). Circles frames are the same as before this feature.

## 3. The type through the API

Post a short WAV with `image_type=circles_paint`: 200, `"image_type": "circles_paint"`, every frame a 600 × 400 PNG; frame 1 contains everything frame 0 contains (outside the new circles). `image_type=circle_paint` or `Circles_paint`: 400 with the message that lists five names. `circle_memory=99`: 400 as for Circles; `circle_memory=500`: 200 and the frames equal those without it.

## 4. Time and room (60 second file, 1,800 frames)

```text
.venv\Scripts\python <scratchpad>\paint_proto.py
```

Expected: well under a minute at the default and the largest settings, and no slower than Circles (the prototype measured 4.4 s and 2.5 s); the room of the frames is of the same order as Circles' (332 and 78 MB, against 113 and 130 MB).

## 5. The page (manual: this tooling has no browser)

Start the backend and the frontend and check:

1. The Image type dropdown offers five choices; choosing Circles paint shows a group "Circles paint" with Movement, Radius, Resize by volume and Notes (no Memory), Data smoothing, and no Image smoothing.
2. Switching between Circles and Circles paint keeps Movement, Radius, Resize by volume and Notes; Circles shows Memory again.
3. Create frames and play: the canvas builds up frame after frame and nothing disappears; the summary says "Image type: Circles paint" with the four values and no Memory.
4. The info text of Image type describes Circles paint.

Record any visual problem found here; the rules are in `contracts/circles-paint.md`.
