# Data Model: Code Readability Documentation

This feature has no stored data. Its "data" is the **vocabulary** that the documentation uses: the kinds of arrays (each one a named alias with one canonical description) and the shared steps of a job. Both are **first drafts from reading the code**; the final lists are written in `array_types.py` and in the overview of `image_types.py`, and every shape is confirmed with the shape probe (research D6) and every step order with the pipeline trace (research D7) before it is written down.

## Kinds of arrays (the alias vocabulary, draft)

| Alias | Element | Shape | What it represents | Produced by |
|---|---|---|---|---|
| `Samples` | float64 | `(samples,)` | One channel of the audio, scaled to about -1 to 1 (integer files are divided by their full scale) | `note_analysis.read_wav`, `_to_float` |
| `NoteStrengths` | float64 | `(windows, 88)` or `(frames, 88)` | The strength (magnitude, 0 or more) of each of the 88 piano notes (note 0 = 55 Hz, each next one a semitone higher) in each analysis window, or in each frame once the windows are averaged; never negative | `analyze_channels`, `average_frames`, `smooth_frames` |
| `WindowRanges` | intp | `(frames,)` (three of them) | For each frame, the first window it owns, the window after its last, and the window to fall back to | `frame_rendering.frame_windows` |
| `ImpulseEnergies` | float64 | `(impulses,)` | The energy of each 32-sample impulse window of the whole file: the average of the left and right standard deviations | `local_peaks.impulse_energy` |
| `PeakTimes` | float64 | `(peaks,)` | When each local peak of the energy is, in seconds, strictly increasing | `LocalPeaks` |
| `PeakRates` | float64 | `(peaks,)` | The rate of each peak in beats per minute (60 divided by the seconds since the previous peak; 60 for the first) | `LocalPeak.rate` |
| `Tempos` | float64 | `(peaks,)` | The current tempo after each peak, in beats per minute, always from 60 to 156 | `tempo_finder.find_tempo` |
| `BeatPositions` | float64 | `(frames,)` | The place of the middle of each frame in the local energy peak, from 0 (bottom of the beat) to 1 (top) | `LocalPeaks.frame_positions` |
| `CircleSeries` | float64 | `(peaks, 4)` | The four speeds of Rhythm Circles after each peak, in revolutions per minute, outer ring first | `rhythm_circles.peak_series` |
| `CircleAngles` | float64 | `(frames, 4)` | The angle of each Rhythm Circles ring at the middle of each frame, in turns, clockwise, not wrapped | `rhythm_circles.rhythm_angles` |
| `Points` | float64 | `(frames, 84)` or `(frames, 12)` | The points (0 to 64) each circle of Decay, Decay Exp (84 notes) or Chromatic Decay (12 letters) holds in each frame | `decay`, `decay_exp`, `chromatic_decay` |
| `RingLevels` | float64 | `(frames, 12)` | The distance from the top of the beat (0 to 1) of each of the 12 rings of the Chromatic Decay target in each frame | `chromatic_decay.ring_levels` |
| `ColorTable` | uint8 | `(256, 3)` | The RGB color of each of the 256 steps of a colormap | `colormaps.lookup_table` |
| `Pictures` | uint8 | `(height, width, 3)` | One RGB picture (a frame) | each image type's drawing |
| `Indices` | intp | `(n,)` | Positions in another array (for example the order of the notes in a layout) | `note_layout`, `note_selection` |

Others the code needs (the polar bars, the energy histograms, the wireframe lines and heights, the grids of 7 rows by 12 columns, masks, edges) are added when their modules are documented; each gets one row here before it is used in a signature.

**Rules for the vocabulary**: one alias per kind of array, never two names for the same kind; an alias name says what the numbers are, not how they are stored; an array that has the same meaning in two functions uses the same alias and the same words; the description lives only in `array_types.py`, and a function's docstring gives the concrete shape for itself and refers to the alias.

## The aliases as built (generated from `backend/app/services/array_types.py`, 2026-11-15)

The table above was the first draft. `array_types.py` is the one place with the description of each kind (shape, meaning, made by); these 76 aliases exist:

| Alias | Element | What it is |
|---|---|---|
| `ArrayLike` |  | an input that the function turns into an array itself. |
| `RawSamples` | number | one channel of a WAV file exactly as it was read. |
| `Samples` | float64 | one channel of the audio, scaled. |
| `NoteStrengths` | float64 | the strength of each of the 88 piano notes, for each analysis window or for each frame. |
| `WindowRanges` | intp | for each frame, which analysis windows it owns. |
| `GridValues` | float64 | the values of the cells of a grid, for each frame. |
| `PixelEdges` | int64 | where the cells of a row or a column of a grid start and end, in pixels. |
| `FrameGrid` | float64 | the values of one frame laid out as a grid. |
| `HiddenMask` | bool_ | which values are too faint to show. |
| `WavePattern` | float64 | the rings of the beat wave of the contour. |
| `WaveModifier` | float64 | the factor that the beat wave multiplies a frame's grid by. |
| `Indices` | intp | positions in another array. |
| `NoteFrequencies` | float64 | the frequencies of the 88 notes. |
| `WindowStarts` | int64 | where each analysis window starts, in whole samples. |
| `WindowPositions` | float64 | where each analysis window starts, exactly. |
| `WindowTimes` | float64 | when each analysis window starts, in seconds. |
| `LetterStrengths` | float64 | the strength of each of the 12 letters (note names), for each analysis window. |
| `LetterNotes` | intp | the note that stands for each letter. |
| `Scores` | number | one number of the score of a chord match, for each analysis window. |
| `WindowFlags` | bool_ | a yes or no for each analysis window. |
| `ChordTypeIndexes` | int16 | the chord type found in each analysis window. |
| `ChordInversions` | int8 | the inversion of the chord found in each analysis window. |
| `ChordNotes` | int16 | the notes of the chord found in each analysis window. |
| `PeakSamples` | float64 | where the local peaks are, in samples. |
| `PeakEnergies` | float64 | an energy for each local peak. |
| `PointValues` | float64 | one value for each point of the file that was asked about. |
| `ImpulseEnergies` | float64 | the loudness of the file, in short steps. |
| `PeakTimes` | float64 | when the local peaks of the energy are. |
| `PeakRates` | float64 | how fast the local peaks follow each other. |
| `Tempos` | float64 | the current tempo of the tempo finder. |
| `BeatPositions` | float64 | where each frame is in the local energy peak. |
| `CircleSeries` | float64 | the speeds of the four rings of Rhythm Circles after each local peak. |
| `CircleAngles` | float64 | the angle of the four rings of Rhythm Circles in each frame. |
| `CirclePoints` | float64 | the points that each circle holds. |
| `PointGains` | float64 | the points that each note (or letter) gains in each frame. |
| `GivePerFrame` | float64 | how many points each circle gives to each neighbour in one frame. |
| `PointsGiven` | float64 | how many points each circle gives away in one decay step. |
| `CircleRadii` | float64 | the radius of each circle. |
| `RingPositions` | float64 | where on the colormap each ring of each circle is. |
| `RingColors` | uint8 | the color of each ring of each circle. |
| `CircleColors` | uint8 | the color at the center of each circle. |
| `PixelCells` | int32 | which cell each pixel of the picture is in. |
| `PixelDistances` | floating | how far each pixel is from the center of a circle. |
| `RingWeights` | float32 | how much each ring of a circle shows in each pixel of its cell. |
| `Rgb` | number | one color. |
| `FrameTapers` | float64 | the taper of Decay Exp in each frame. |
| `LetterEnergies` | float64 | the energy of each of the 12 letters in each frame. |
| `BeatDistances` | float64 | how far each frame is from the top of the beat. |
| `RingLevels` | float64 | how far from the top of the beat each ring of the target is, in each frame. |
| `TargetColors` | uint8 | the colors of the rings of the target of the beat. |
| `LineAngles` | float64 | the angle of the sine that each letter adds at each sample of a line. |
| `LineSums` | float64 | the sum of the 12 waves at each sample of a line. |
| `LineX` | float64 | where the samples of a line are across the picture. |
| `LineHeights` | float64 | the height of a line above its base. |
| `ScreenCoordinates` | float64 | one coordinate of each point of a line on the screen. |
| `LineColors` | uint8 | the color of the line of each frame. |
| `BarArcs` | int16 | the arc of the circle that each note bar is in, in each frame. |
| `BarStrengths` | float64 | how strong the note or chord of each bar is. |
| `ChordPlaces` | int16 | the arc of the chord bar in each frame. |
| `BarLengths` | float64 | how far the bars of each frame reach. |
| `PixelNumbers` | intp | pixels of the picture, by their flat number. |
| `PixelWeights` | floating | how much of each pixel belongs to an arc. |
| `CenterDistances` | floating | how far each pixel is from the center of the picture. |
| `BarColors` | float32 | the color of each bar. |
| `Coverage` | float32 | how much of each pixel the bars of one layer cover. |
| `PremultipliedColors` | float32 | the colors of the bars of one layer, already multiplied by how much of each pixel they cover. |
| `RankScores` | int64 | the rank points that each note scores in each analysis window. |
| `QuasiDecibels` | float64 | what each note adds to its amplitude total in each analysis window. |
| `EnergyTotals` | number | the running totals of a data set of Energy Graphs, in each frame. |
| `BarShares` | float64 | the share of each note in a data set of Energy Graphs. |
| `CircleSpeeds` | float64 | the speed of the four rings of Rhythm Circles at each moment. |
| `Moments` | float64 | times of the file to ask about. |
| `PixelAngles` | float32 | the direction of each pixel from the center of the picture. |
| `ColorList` | float32 | a list of colors. |
| `ColorTable` | uint8 | the colors of a colormap. |
| `Pictures` | uint8 | one picture, a frame of the animation. |

## The shared steps of a job (draft for the overview)

In the order of a job (`routers/jobs.py` and `frame_rendering.write_frames`):

| Step | What happens | Function | Data after it |
|---|---|---|---|
| READ | The WAV file is read as two channels | `note_analysis.read_wav` | two `Samples` `(samples,)` and the sample rate |
| ANALYZE | Each window of the audio becomes 88 note strengths | `note_analysis.analyze_channels` | `NoteStrengths` `(windows, 88)` |
| FLOOR | A note more than 60 dB below the loudest of the file is set to 0 | `noise_floor.floor_analysis` | `NoteStrengths` `(windows, 88)` |
| MEASURE | (only for types that use it) The local peaks of the whole energy are found, and turned into: the beat position of each frame; or the tempo and the angles of the rings; or the energy of each frame | `local_peaks.measure_local_peaks`, `tempo_finder.find_tempo`, `rhythm_circles.rhythm_angles`, `energy_graphs.frame_energy` | `BeatPositions` `(frames,)`, `CircleAngles` `(frames, 4)` or the frame energies |
| AVERAGE | The windows are averaged into one row per frame | `frame_rendering.average_frames` | `NoteStrengths` `(frames, 88)` |
| SMOOTH | Each frame is mixed with the frames before it | `frame_rendering.smooth_frames` | `NoteStrengths` `(frames, 88)` |
| DRAW | The type's own stages make a picture of each frame (see the rows of the overview) | one drawing function per type | `Pictures` `(height, width, 3)` |
| SAVE | Each picture is written as a PNG, and the frame rate as `render.json` | `frame_saving`, `write_frames` | the files |

**Which type uses which step** (to be confirmed by the trace): MEASURE for the beat is used by Decay, Decay Exp, Polar Chords, Chromatic Decay, Chromatic Wireframe and by Contour only with Beat coloring on; MEASURE for the rings by Rhythm Circles (no beat); MEASURE for the frame energy by Energy Graphs; SMOOTH is applied to every type but Rhythm Circles (its data is not note values).

## Validation rules (what the checks enforce)

- Every function and method of `backend/app` has a type on every parameter (except `self`, `cls`) and on its return value (nested functions included).
- Every top-level function or method with an array alias or `ndarray` in its signature names each of its array parameters in its docstring.
- Every module is in exactly one of two lists in the presence check: processing (needs "Order of operations") or exempt (needs "No data processing").
- Every alias in `array_types.py` has a description comment; `image_types.py` names all 8 types in its overview.
