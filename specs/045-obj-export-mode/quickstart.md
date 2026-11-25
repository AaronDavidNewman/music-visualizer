# Quickstart: how to see the 3D export work

Prerequisites: backend and frontend running (`uvicorn app.main:app` in `backend`, `npm run dev` in `frontend`), a short `.wav` with a few notes and a clear pulse (a few seconds), Blender
(optional, for scenario 4). The automated checks are in `backend/tests/test_obj_export.py`, `backend/tests/test_obj_export_api.py` and the frontend tests; run them with
`backend/.venv/Scripts/python.exe -m pytest backend/tests` and `npx vitest run` in `frontend`.

## Scenario 1: Contour (User Story 1)

1. Choose **Contour**; the group **3D export** is shown. Turn on **Export 3D files (.obj)**, frame rate 10, **Create frames**.
2. Expected: the usual pictures and, in the result list, `3D export: yes` and a link **Download 3D files (.zip)**.
3. Download and unpack: one `frame_NNNNNN.obj` for each frame, numbered like the pictures. Open one in a text editor: three lines of comments, `o frame_...`, 84 lines `v x y z r g b` (X from 0 to
   11, Y from 0 to 6, Z from 0 to 12, colors between 0 and 1), then 66 lines `f a b c d`.
4. A frame in which the music is silent: 84 points all with Z = 0 and the same color.

## Scenario 2: Chromatic Wireframe (User Story 2)

1. Choose **Chromatic Wireframe**, turn on the export, **Create frames** with at least 12 frames.
2. Expected: the file of frame 0 has 12 points and no faces; the file of frame 5 has 72 points and 55 faces; from frame 11 on 144 points and 121 faces. X is the letter (0 to 11), Y the age of the
   line (0 = this frame, 11 = eleven frames earlier), Z from 1 to 12; the 12 points of a line have one color, the color the picture gives the line.

## Scenario 3: The option and the refusals (User Story 3)

1. Choose any other picture (for example Decay): the group **3D export** is not shown.
2. With Contour chosen and the option off: no link, no `.obj` files, the pictures are the same as before.
3. With the API: `curl -F file=@song.wav -F image_type=decay -F export_obj=true http://localhost:8000/api/jobs` answers 400 `The 3D export is only available for Contour and Chromatic Wireframe.`;
   `-F export_obj=maybe` answers 400 `The 3D export must be true or false.`; `GET /api/jobs/<id>/obj` of a job without export answers 404 `No 3D export was made for this render.`

## Scenario 4: In Blender (the aim of the feature)

1. File, Import, Wavefront (.obj), choose one frame. The 12 x 7 surface (or the stack of 12 lines) appears with Z up; the faces are lit from above; the vertex colors are available as a color
   attribute (the values are 0 to 1).
2. Add a Subdivision Surface modifier: the flat faces become a smooth surface; for the wireframe this is where the curve comes from, the points of the file being the 12 amplitudes of each line.

## Scenario 5: Same input, same files; the pictures do not change

1. Make the same job twice: the two ZIPs have identical files.
2. Make the job with the export on and off: the PNG frames are identical byte for byte.
3. `python specs/045-obj-export-mode/tools/verify_drawing.py` (made from 043's): all pictures identical to the baseline made before the change.
