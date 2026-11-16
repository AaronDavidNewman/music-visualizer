"""The kinds of arrays that the application passes from one step to the next, one name for each kind.

No data processing: this module only holds the names (type aliases for NumPy arrays) and, beside each, the one
description of what that kind of array is. The type of an array says nothing about what its numbers mean or about its
shape, so a function that takes or returns an array is annotated with one of these names and its docstring gives the
concrete shape for that function (``specs/041-code-readability-docs/contracts/documentation-standard.md``). To find out
what a name means, search for it here.

How to read a description: **Shape** names the axes (``windows`` is one analysis window of the audio, ``frames`` one
picture of the animation, ``peaks`` one local peak of the energy of the file, and so on); **Meaning** is what each
number is, with its unit or range; **Made by** is the function that produces it.

Only NumPy is imported here, so every module can import these names without an import cycle.
"""

import numpy as np
import numpy.typing as npt

# --- anything that can become an array --------------------------------------------------------------------------------

# ArrayLike: an input that the function turns into an array itself.
#   Shape: stated by each function (a list or tuple of numbers, or an array, one or two dimensional).
#   Meaning: the quantity is stated by each function in its docstring; the function checks the shape and the numbers
#            (and refuses what does not fit) before using them.
#   Made by: the caller (a list of numbers, a tuple, or an array of any kind).
ArrayLike = npt.ArrayLike

# --- the audio --------------------------------------------------------------------------------------------------------

# RawSamples: one channel of a WAV file exactly as it was read.
#   Shape: ``(samples,)``.
#   Meaning: the amplitude of each sample in the units of the file (integers for 8, 16, 24 and 32 bit files, floating
#            point for float files); the range depends on the bit depth of the file, so it is scaled before anything is
#            measured.
#   Made by: ``note_analysis.read_wav``.
RawSamples = npt.NDArray[np.number]

# Samples: one channel of the audio, scaled.
#   Shape: ``(samples,)``.
#   Meaning: the amplitude of each sample as a floating point number scaled so that the full range of the file is about
#            -1 to 1; the bit depth of the file no longer matters.
#   Made by: ``note_analysis._to_float`` (from ``RawSamples``).
Samples = npt.NDArray[np.float64]

# --- the notes --------------------------------------------------------------------------------------------------------

# NoteStrengths: the strength of each of the 88 piano notes, for each analysis window or for each frame.
#   Shape: ``(windows, 88)`` right after the analysis, ``(frames, 88)`` once the windows are averaged into frames and
#          after the frames are smoothed; the last axis is the note: index 0 is the note of 55 Hz and each next index is
#          one semitone higher (index 87 is about 7040 Hz). Where only the 84 notes that are drawn are meant, the last
#          axis is 84.
#   Meaning: the strength of the note in that window or frame (the magnitude of the spectrum at the note's frequency,
#            averaged over the two channels): 0 or more, never negative, in the units of the scaled samples, with no
#            fixed upper limit (the pictures scale it to the loudest value of the file).
#   Made by: ``note_analysis.analyze_channels`` (windows), ``frame_rendering.average_frames`` (frames),
#            ``frame_rendering.smooth_frames`` (smoothed frames).
NoteStrengths = npt.NDArray[np.float64]

# WindowRanges: for each frame, which analysis windows it owns.
#   Shape: ``(frames,)`` (``frame_rendering.frame_windows`` returns three of them: ``first``, ``stop`` and ``earlier``).
#   Meaning: window numbers, counted from 0 in time order: the first window the frame owns, the window after the last it
#            owns, and the last window that started before the frame (the one to fall back to when the frame owns none).
#   Made by: ``frame_rendering.frame_windows``.
WindowRanges = npt.NDArray[np.intp]

# GridValues: the values of the cells of a grid, for each frame.
#   Shape: ``(frames, cells)``: one row for each frame, one column for each cell of the grid in row-major order (the
#          cell at row ``y`` and column ``x`` is column ``y * columns + x``); for the grid of the drawn notes, ``cells``
#          is 84 (7 rows by 12 columns), and a finer grid (the resolution setting) has ``r * r`` times as many cells.
#   Meaning: one value for each cell, in the same units as ``NoteStrengths`` (0 or more) when the cells hold note
#            strengths; which note is in which cell is decided by ``note_layout``.
#   Made by: ``note_layout.arrange_notes``, ``resolution.interpolate_grid``.
GridValues = npt.NDArray[np.float64]

# PixelEdges: where the cells of a row or a column of a grid start and end, in pixels.
#   Shape: ``(cells + 1,)``: the left (or top) edge of each cell and the right (or bottom) edge of the last.
#   Meaning: pixel positions from 0 to the size of the picture, increasing; the nearest whole pixel to an even split.
#   Made by: ``note_grid.tile_edges``.
PixelEdges = npt.NDArray[np.int64]

# FrameGrid: the values of one frame laid out as a grid.
#   Shape: ``(rows, columns)``: ``rows`` and ``columns`` of the grid being drawn (7 by 12 for the drawn notes, ``7 r``
#          by ``12 r`` at resolution ``r``).
#   Meaning: the smoothed value of the cell at each row and column, 0 or more (one frame of ``GridValues`` reshaped);
#            for the contour the rows are flipped so that the first row of notes is drawn at the top of the picture.
#   Made by: ``contour.write_contour_frames`` (from one row of ``GridValues``).
FrameGrid = npt.NDArray[np.float64]

# HiddenMask: which values are too faint to show.
#   Shape: the shape of the values that it was made from (any grid or list).
#   Meaning: True where the value is strictly below the threshold (a percentage of the largest value of the file) and is
#            to be shown as 0; False where it is shown.
#   Made by: ``frame_rendering.hidden_below``.
HiddenMask = npt.NDArray[np.bool_]

# WavePattern: the rings of the beat wave of the contour.
#   Shape: ``(rows, columns)``: the shape of the grid the contour is drawn from.
#   Meaning: a number from 0 to 1 for each cell: 1 on the crest of a ring, 0 between two rings, 0.5 at the center;
#            depends only on the shape and the number of waves; read-only.
#   Made by: ``beat_wave.wave_pattern``.
WavePattern = npt.NDArray[np.float64]

# WaveModifier: the factor that the beat wave multiplies a frame's grid by.
#   Shape: ``(rows, columns)``: the shape of the grid the contour is drawn from.
#   Meaning: a number from 0 to 1 for each cell: ``1 - pattern * sin(pi * k)`` for a frame at place ``k`` (0 to 1) in
#            the local energy peak; 1 means the value is left as it is.
#   Made by: ``beat_wave.wave_modifier``.
WaveModifier = npt.NDArray[np.float64]

# Indices: positions in another array.
#   Shape: ``(n,)`` (``n`` is stated by each function).
#   Meaning: whole numbers that are indices into a list or an axis of another array (for example the order in which
#            notes are placed, or the notes that are kept); the other array is named in the docstring of the function.
#   Made by: ``note_layout``, ``note_selection``.
Indices = npt.NDArray[np.intp]

# NoteFrequencies: the frequencies of the 88 notes.
#   Shape: ``(88,)``: one entry for each note, from the lowest (index 0) to the highest (index 87).
#   Meaning: the frequency of the note in hertz: 55 Hz for index 0, each next one a semitone (a factor of 2 to the power
#            1/12) higher.
#   Made by: ``note_analysis.note_frequencies``.
NoteFrequencies = npt.NDArray[np.float64]

# WindowStarts: where each analysis window starts, in whole samples.
#   Shape: ``(windows,)``: one entry for each analysis window of the file, in time order.
#   Meaning: the number of the first sample of the window (counted from 0): the nearest whole sample to ``k * step``.
#   Made by: ``note_analysis.window_starts``, ``AnalysisResult.window_starts``.
WindowStarts = npt.NDArray[np.int64]

# WindowPositions: where each analysis window starts, exactly.
#   Shape: ``(windows,)``: one entry for each analysis window, in time order.
#   Meaning: the exact start of the window in samples (``k * step``, not rounded), used to decide which frame owns which
#            window.
#   Made by: ``AnalysisResult.window_positions``.
WindowPositions = npt.NDArray[np.float64]

# WindowTimes: when each analysis window starts, in seconds.
#   Shape: ``(windows,)``: one entry for each analysis window, in time order.
#   Meaning: the start of the window in seconds from the start of the file.
#   Made by: ``AnalysisResult.window_start_times``.
WindowTimes = npt.NDArray[np.float64]

# --- the chords -------------------------------------------------------------------------------------------------------

# LetterStrengths: the strength of each of the 12 letters (note names), for each analysis window.
#   Shape: ``(windows, 12)``: the last axis is the letter, 0 for the note name of the lowest column (A) and each next
#          one a semitone higher.
#   Meaning: the strengths of the 7 octaves of the note name added up (an octave is the same note): 0 or more.
#   Made by: ``chords._letters``.
LetterStrengths = npt.NDArray[np.float64]

# LetterNotes: the note that stands for each letter.
#   Shape: ``(windows, 12)``: the last axis is the letter, as in ``LetterStrengths``.
#   Meaning: the note number (0 to 83, 0 is the lowest drawn note) of the loudest octave of the letter in that window,
#            the lowest octave on a tie.
#   Made by: ``chords._letters``.
LetterNotes = npt.NDArray[np.intp]

# Scores: one number of the score of a chord match, for each analysis window.
#   Shape: ``(windows,)``.
#   Meaning: one kind of score (the number of intervals, the loudness of the letters, the widest interval, the
#            inversion, the order of the choice); several kinds are compared one after the other, and a larger number is
#            better.
#   Made by: ``chords.measure_chords``.
Scores = npt.NDArray[np.number]

# WindowFlags: a yes or no for each analysis window.
#   Shape: ``(windows,)``: one entry for each analysis window.
#   Meaning: True or False (here: whether the match being tried is better than the best so far in that window).
#   Made by: ``chords._greater``.
WindowFlags = npt.NDArray[np.bool_]

# ChordTypeIndexes: the chord type found in each analysis window.
#   Shape: ``(windows,)``: one entry for each analysis window.
#   Meaning: an index into the list of chord types that were asked for (``ChordSeries.chord_types``); -1 means no chord
#            was found.
#   Made by: ``chords.measure_chords``.
ChordTypeIndexes = npt.NDArray[np.int16]

# ChordInversions: the inversion of the chord found in each analysis window.
#   Shape: ``(windows,)``.
#   Meaning: 0 for the root position, 1 and more for the inversions; -1 means no chord was found.
#   Made by: ``chords.measure_chords``.
ChordInversions = npt.NDArray[np.int8]

# ChordNotes: the notes of the chord found in each analysis window.
#   Shape: ``(windows, 4)``: up to four notes, lowest first.
#   Meaning: the note numbers (0 to 83, 0 is the lowest drawn note) of the loudest octave of each letter of the chord as
#            they sound; -1 pads the unused entries and means no chord in a window with none.
#   Made by: ``chords.measure_chords``.
ChordNotes = npt.NDArray[np.int16]

# --- the local peaks, the beat and the tempo --------------------------------------------------------------------------

# PeakSamples: where the local peaks are, in samples.
#   Shape: ``(peaks,)``, one entry for each local peak, strictly increasing.
#   Meaning: the number of the first sample of the impulse window where the peak is (so exact to 32 samples), as
#            floating point numbers.
#   Made by: ``LocalPeaks._samples`` (from ``LocalPeak.sample``).
PeakSamples = npt.NDArray[np.float64]

# PeakEnergies: an energy for each local peak.
#   Shape: ``(peaks,)``, one entry for each local peak.
#   Meaning: the impulse energy at the peak, or the smallest or the largest impulse energy of the peaks window (about
#            three seconds) in which the peak was found: 0 or more.
#   Made by: ``LocalPeaks._energies``, ``LocalPeaks._window_mins``, ``LocalPeaks._window_maxs``.
PeakEnergies = npt.NDArray[np.float64]

# PointValues: one value for each point of the file that was asked about.
#   Shape: the shape of the points asked: ``()`` for one point, ``(points,)`` for a list of them.
#   Meaning: the quantity of the function (the interpolated energy, the rate in beats per minute, or the place in the
#            beat from 0 to 1) at each point; the points are sample numbers, or seconds for the functions whose name
#            ends in ``_at_time``.
#   Made by: ``LocalPeaks.energy_at``, ``rate_at``, ``position_at`` and their ``_at_time`` forms.
PointValues = npt.NDArray[np.float64]

# ImpulseEnergies: the loudness of the file, in short steps.
#   Shape: ``(impulses,)``: one entry for each window of 32 samples of the file, in time order.
#   Meaning: the energy of each window of 32 samples (the average of the standard deviation of the left channel and that
#            of the right channel, of the scaled samples): 0 or more.
#   Made by: ``local_peaks.impulse_energy``.
ImpulseEnergies = npt.NDArray[np.float64]

# PeakTimes: when the local peaks of the energy are.
#   Shape: ``(peaks,)``, one entry for each local peak, strictly increasing.
#   Meaning: the time of each peak in seconds from the start of the file.
#   Made by: ``LocalPeaks`` (the sample of each peak divided by the sample rate of the file).
PeakTimes = npt.NDArray[np.float64]

# PeakRates: how fast the local peaks follow each other.
#   Shape: ``(peaks,)``, one entry for each local peak.
#   Meaning: the rate of each peak in beats per minute: 60 times the sample rate divided by the samples since the
#            previous peak (60 for the first peak, which has none).
#   Made by: ``LocalPeak.rate``.
PeakRates = npt.NDArray[np.float64]

# Tempos: the current tempo of the tempo finder.
#   Shape: ``(peaks,)``, one entry for each local peak.
#   Meaning: the current tempo after each peak, in beats per minute, always from 60 to 156 (120 before the second peak).
#   Made by: ``tempo_finder.find_tempo``.
Tempos = npt.NDArray[np.float64]

# BeatPositions: where each frame is in the local energy peak.
#   Shape: ``(frames,)``, one entry for each frame.
#   Meaning: the place of the middle of the frame in the beat, from 0 (the bottom of the beat, or far from any peak) to
#            1 (the top of a peak).
#   Made by: ``LocalPeaks.frame_positions``.
BeatPositions = npt.NDArray[np.float64]

# --- Rhythm Circles ---------------------------------------------------------------------------------------------------

# CircleSeries: the speeds of the four rings of Rhythm Circles after each local peak.
#   Shape: ``(peaks, 4)``: one row for each local peak; the columns are the rings from the outer one to the innermost:
#          the current tempo, its rate of change, the local peak's own rate, its rate of change.
#   Meaning: revolutions per minute (the levels are beats per minute; a rate of change is beats per minute per second,
#            drawn as revolutions per minute); negative turns the ring counterclockwise.
#   Made by: ``rhythm_circles.peak_series``.
CircleSeries = npt.NDArray[np.float64]

# CircleAngles: the angle of the four rings of Rhythm Circles in each frame.
#   Shape: ``(frames, 4)``: one row for each frame (or for each moment asked about, ``(moments, 4)``; ``(4,)`` for one
#          frame); the columns are the rings in the same order as ``CircleSeries``.
#   Meaning: the angle of the notch of each ring at the middle of the frame, in turns (1.0 is a full turn), clockwise
#            positive, not wrapped to one turn.
#   Made by: ``rhythm_circles.rhythm_angles``, ``rhythm_circles.circle_angles``.
CircleAngles = npt.NDArray[np.float64]

# --- the circles of Decay, Decay Exp, Chromatic Decay and Chromatic Wireframe -----------------------------------------

# CirclePoints: the points that each circle holds.
#   Shape: ``(frames, circles)`` for all frames (``circles`` is 84 for Decay and Decay Exp, in cell order row by row,
#          and 12 for Chromatic Decay and Chromatic Wireframe, one for each letter in the order of the ring);
#          ``(circles,)`` for one frame; ``(7, 12)`` for one frame of the 84 laid out as the grid (rows are octaves,
#          columns note names).
#   Meaning: the points of the circle at the end of the frame, from 0 to 64 (0 before the first frame): they decide the
#            size, the color and the rings of its disc.
#   Made by: ``decay.circle_points``, ``decay_exp.circle_points``, ``chromatic_decay.circle_points``.
CirclePoints = npt.NDArray[np.float64]

# PointGains: the points that each note (or letter) gains in each frame.
#   Shape: ``(frames, 84)``: one row for each frame, one column for each of the 84 drawn notes in note order (not cell
#          order), for Decay and Decay Exp; ``(frames, 12)``, one column for each letter (A is 0), for Chromatic Decay
#          and Chromatic Wireframe.
#   Meaning: 0 for every note (or letter) but the five loudest of the frame; those gain 24, 20, 16, 12 and 8 points
#            (loudest first) plus up to 8 more at the top of the beat; for Decay Exp and the chromatic types each gain
#            ``g`` is then cut back to ``g * exp(-g / taper)``.
#   Made by: ``decay.gains``, ``decay_exp.exp_gains``, ``chromatic_decay._raw_gains``, ``chromatic_decay.letter_gains``.
PointGains = npt.NDArray[np.float64]

# GivePerFrame: how many points each circle gives to each neighbour in one frame.
#   Shape: the shape of the points it was made from (``(7, 12)`` or ``(12,)`` for one frame, or any shape).
#   Meaning: points per neighbour per frame: 0 for a circle with no points, then the decay amount of the circle's
#            saturation level (low, medium, high or saturated).
#   Made by: ``decay.decay_per_frame``, ``decay_exp.exp_loss_per_frame``.
GivePerFrame = npt.NDArray[np.float64]

# PointsGiven: how many points each circle gives away in one decay step.
#   Shape: ``(7, 12)``: one entry for each cell of the grid.
#   Meaning: the total points the circle gives to its neighbours in the step (never more than it has): an eighth of it
#            goes to each neighbour; what the missing neighbours of an edge or corner circle would have received is
#            lost.
#   Made by: ``decay.decay_step``, ``decay_exp.decay_exp_step``.
PointsGiven = npt.NDArray[np.float64]

# CircleRadii: the radius of each circle.
#   Shape: the shape of the points it was made from (``(84,)`` or ``(12,)`` for one frame, or ``(frames, circles)``).
#   Meaning: the radius in pixels: one twelfth of the full radius at 0 points, the full radius from 24 points on.
#   Made by: ``decay.circle_radii``, ``chromatic_decay.circle_radii``.
CircleRadii = npt.NDArray[np.float64]

# RingPositions: where on the colormap each ring of each circle is.
#   Shape: the shape of the points it was made from plus a last axis of 12: ``(84, 12)`` for one frame of Decay,
#          ``(12, 12)`` for one frame of Chromatic Decay.
#   Meaning: a place on the colormap from 0 (its first color) to 1 (its last) for each of the twelve rings of the
#            circle, ring 1 (at the center) first.
#   Made by: ``decay.ring_positions``.
RingPositions = npt.NDArray[np.float64]

# RingColors: the color of each ring of each circle.
#   Shape: the shape of the points it was made from plus ``(12, 3)``: ``(84, 12, 3)`` for one frame of Decay,
#          ``(12, 12, 3)`` for one frame of Chromatic Decay.
#   Meaning: the red, green and blue (0 to 255) of each of the twelve rings of the circle, ring 1 (at the center) first.
#   Made by: ``decay.ring_colors``.
RingColors = npt.NDArray[np.uint8]

# CircleColors: the color at the center of each circle.
#   Shape: the shape of the points it was made from plus a last axis of 3 (red, green, blue).
#   Meaning: the color of ring 1: the one color of a flat circle (up to 32 points), each channel from 0 to 255.
#   Made by: ``decay.circle_colors``.
CircleColors = npt.NDArray[np.uint8]

# PixelCells: which cell each pixel of the picture is in.
#   Shape: ``(height * width,)``: one entry for each pixel of the picture, row by row.
#   Meaning: the number of the cell of the grid (0 to 83, row by row) that contains the pixel.
#   Made by: ``decay._geometry``.
PixelCells = npt.NDArray[np.int32]

# PixelDistances: how far each pixel is from the center of a circle.
#   Shape: ``(height, width)`` of the picture (Decay: each pixel from the center of its cell), or ``(rows, columns)`` of
#          the box around a circle (the chromatic types).
#   Meaning: the distance in pixels from the center of the circle (the middle of the pixel is taken as its position).
#   Made by: ``decay._geometry``, ``chromatic_decay._geometry``, ``chromatic_decay._peak_geometry``.
PixelDistances = npt.NDArray[np.floating]

# RingWeights: how much each ring of a circle shows in each pixel of its cell.
#   Shape: ``(cell height * cell width, 12)``: one row for each pixel of the cell, row by row; one column for each of
#          the 12 rings.
#   Meaning: the share (0 to 1; each row adds up to 1) of the ring in the pixel: the ring the pixel is in, less the
#            shares that the rings on either side reach into it for a smooth edge.
#   Made by: ``decay._geometry``.
RingWeights = npt.NDArray[np.float32]

# Rgb: one color.
#   Shape: ``(3,)``: red, green, blue.
#   Meaning: the color with each channel from 0 to 255, as whole numbers (a row of a ``ColorTable``) or as floating
#            point numbers (when colors are blended without rounding).
#   Made by: the drawing of each picture (the background, the first and the last color of a ring).
Rgb = npt.NDArray[np.number]

# FrameTapers: the taper of Decay Exp in each frame.
#   Shape: ``(frames,)``: one entry for each frame.
#   Meaning: the number ``taper`` in the cut ``g * exp(-g / taper)`` that the points a circle gains are multiplied by in
#            that frame: from 8 to 12, 8 for the first frame.
#   Made by: ``decay_exp.circle_tapers``, ``decay_exp._simulate``.
FrameTapers = npt.NDArray[np.float64]

# --- Chromatic Decay and Chromatic Wireframe --------------------------------------------------------------------------

# LetterEnergies: the energy of each of the 12 letters in each frame.
#   Shape: ``(frames, 12)``: one row for each frame, one column for each letter (the note name without its octave; 0 is
#          A, then A#, B, C, ... G# is 11).
#   Meaning: the largest of the strengths of the 7 octaves of the letter in that frame (not their sum): 0 or more.
#   Made by: ``chromatic_decay.letter_energies``.
LetterEnergies = npt.NDArray[np.float64]

# BeatDistances: how far each frame is from the top of the beat.
#   Shape: ``(frames,)``: one entry for each frame.
#   Meaning: from 0 (at the top of a local energy peak) to 1 (far from a peak, or at its bottom): ``1 - position`` or,
#            stretched over the range of the beat of the file so that the whole colormap is used, ``beat_distances``.
#   Made by: ``chromatic_decay.peak_distances``, ``chromatic_decay.beat_distances``.
BeatDistances = npt.NDArray[np.float64]

# RingLevels: how far from the top of the beat each ring of the target is, in each frame.
#   Shape: ``(frames, 12)``: one row for each frame, one column for each of the 12 rings of the target, the center ring
#          first.
#   Meaning: a distance from the top of the beat, 0 to 1: the center ring shows the current frame's distance, ring ``k``
#            the average of the distances of two earlier frames.
#   Made by: ``chromatic_decay.ring_levels``.
RingLevels = npt.NDArray[np.float64]

# TargetColors: the colors of the rings of the target of the beat.
#   Shape: ``(frames, 12, 3)`` for all frames, ``(12, 3)`` for one frame: one color for each of the 12 rings, the center
#          ring first; red, green, blue.
#   Meaning: the row of the colormap at the ring's level (0 to 255 each channel): the first color at the top of the
#            beat, the last far from it.
#   Made by: ``chromatic_decay.ring_colors_of``.
TargetColors = npt.NDArray[np.uint8]

# --- Chromatic Wireframe ----------------------------------------------------------------------------------------------

# LineAngles: the angle of the sine that each letter adds at each sample of a line.
#   Shape: ``(12, n)``: one row for each of the 12 letters (A first), one column for each of the ``n`` samples across
#          the plot (two for each pixel).
#   Meaning: the angle in radians: ``2 pi * (points / 16) * u / width of the plot + 2 pi * start / width of the plot``
#            for the letter's points (the frequency) and where its share of the width starts (the phase); the wave added
#            is the sine of it squared.
#   Made by: ``chromatic_wireframe.line_angles``.
LineAngles = npt.NDArray[np.float64]

# LineSums: the sum of the 12 waves at each sample of a line.
#   Shape: ``(n,)``: one entry for each sample across the plot.
#   Meaning: ``S``, from 0 to 1: the 12 waves (each the letter's radius over the full radius times the sine squared)
#            added and divided by 12.
#   Made by: ``chromatic_wireframe.line_sums``.
LineSums = npt.NDArray[np.float64]

# LineX: where the samples of a line are across the picture.
#   Shape: ``(n,)``: one entry for each sample, increasing.
#   Meaning: the position in pixels from the left of the picture, from the margin to the width less the margin, every
#            half pixel; the same for every line.
#   Made by: ``chromatic_wireframe.line_heights``.
LineX = npt.NDArray[np.float64]

# LineHeights: the height of a line above its base.
#   Shape: ``(n,)`` for one line, ``(frames, n)`` for the line of every frame.
#   Meaning: the height in pixels above the base of the line at each sample, from 0 to ``A`` (two fifths of the
#            picture's height): ``A * clip((S - floor) / (ceiling - floor), 0, 1)``.
#   Made by: ``chromatic_wireframe.line_heights``.
LineHeights = npt.NDArray[np.float64]

# ScreenCoordinates: one coordinate of each point of a line on the screen.
#   Shape: ``(n,)``: one entry for each sample of the line.
#   Meaning: the x position (pixels from the left) or the y position (pixels from the top) of the point after the line
#            was moved back and made smaller by its depth.
#   Made by: ``chromatic_wireframe.project_line``.
ScreenCoordinates = npt.NDArray[np.float64]

# LineColors: the color of the line of each frame.
#   Shape: ``(frames, 3)``: one row for each frame; red, green, blue.
#   Meaning: the row of the colormap at the frame's place in the beat (0 to 255 each channel): the last color at the top
#            of a peak, the first at the bottom of the beat.
#   Made by: ``chromatic_wireframe.line_colors``.
LineColors = npt.NDArray[np.uint8]

# --- Polychord --------------------------------------------------------------------------------------------------------

# LoudLetters: the letters of the loudest notes of each frame.
#   Shape: ``(frames, count)``: one row for each frame; one column for each of the loudest notes, loudest first
#          (``count`` is the Number of notes setting, 5 to 8).
#   Meaning: the letter (the chromatic tone without its octave) of the note, 0 for A up to 11 for G#, as in
#            ``chromatic_decay``; -1 where fewer than ``count`` notes sound in the frame.
#   Made by: ``polychord.loudest_letters``.
LoudLetters = npt.NDArray[np.intp]

# LinkTurns: how much each link of a figure turns from the link before it.
#   Shape: ``(frames, count)``: one row for each frame; one column for each link of the figure, the first at the center.
#   Meaning: the turn in degrees, clockwise positive: 0 for the first link, then 30 for each step of a fifth between the
#            letter of the link and the letter of the link before it (from -150 to +180); 0 for a missing link.
#   Made by: ``polychord.link_turns``.
LinkTurns = npt.NDArray[np.float64]

# CopyCounts: how many copies of the figure each frame has.
#   Shape: ``(frames,)``: one entry for each frame.
#   Meaning: a whole number from the minimum to the maximum number of copies: the maximum at the top of the beat, the
#            minimum at its bottom.
#   Made by: ``polychord.copy_counts``.
CopyCounts = npt.NDArray[np.intp]

# FrameTempos: the current tempo at the middle of each frame.
#   Shape: ``(frames,)``: one entry for each frame.
#   Meaning: the tempo in beats per minute that the tempo finder has after the latest local peak, from 60 to 156 (120
#            before the first peak and with no peak).
#   Made by: ``polychord.frame_tempos``.
FrameTempos = npt.NDArray[np.float64]

# StartAngles: where the figure of each frame starts.
#   Shape: ``(frames,)``: one entry for each frame.
#   Meaning: the angle in degrees, clockwise from straight up, of the first link of the first copy: the rotation in
#            degrees per second times the time of the frame in seconds.
#   Made by: ``polychord.start_angles``.
StartAngles = npt.NDArray[np.float64]

# FigureColors: the color of the links of each frame.
#   Shape: ``(frames, 3)``: one row for each frame; red, green, blue.
#   Meaning: the row of the colormap at the tempo's place between 60 and 156 beats per minute (0 to 255 each channel):
#            the first color for the slowest tempo, the last for the fastest; one color for every link of a frame.
#   Made by: ``polychord.tempo_colors``.
FigureColors = npt.NDArray[np.uint8]

# LinkSegments: the pieces of line drawn in one picture.
#   Shape: ``(segments, 2, 2)``: one entry for each piece; its two end points; the x and y of each point.
#   Meaning: positions in pixels from the left and from the top of the picture; the pieces of every copy of the figure,
#            copy 0 first, each link cut into the same number of consecutive pieces.
#   Made by: ``polychord.figure_segments``.
LinkSegments = npt.NDArray[np.float64]

# LinkWidths: how wide each piece of line of a picture is.
#   Shape: ``(segments,)``: one entry for each piece of ``LinkSegments``.
#   Meaning: the width in pixels of the piece, at least 1; it falls along the figure from the center outward, so a link
#            ends as wide as the next one starts.
#   Made by: ``polychord.figure_segments``.
LinkWidths = npt.NDArray[np.float64]

# --- Polar Chords -----------------------------------------------------------------------------------------------------

# BarArcs: the arc of the circle that each note bar is in, in each frame.
#   Shape: ``(frames, volumes)``: one row for each frame; one column for each volume (the loudest note, the second
#          loudest, ... up to the number of notes shown, 5 to 8).
#   Meaning: the number of the arc (0 to 83, each 360 / 84 degrees wide, clockwise from straight up) of the bar of that
#            volume; -1 where there is no bar.
#   Made by: ``polar_chords.note_targets`` (the arcs the bars head for), ``polar_chords.follow_arcs`` (the arcs the bars
#            are in).
BarArcs = npt.NDArray[np.int16]

# BarStrengths: how strong the note or chord of each bar is.
#   Shape: ``(frames, volumes)`` for the note bars, ``(frames,)`` for the chord bar of each frame.
#   Meaning: the square root of the strength as a share of the largest value of the whole file, from 0 to 1 (0 where
#            there is no bar); it decides the color of the bar.
#   Made by: ``polar_chords._targets``, ``polar_chords.polar_bars``.
BarStrengths = npt.NDArray[np.float64]

# ChordPlaces: the arc of the chord bar in each frame.
#   Shape: ``(frames,)``: one entry for each frame.
#   Meaning: ``7 * root letter + the number of the chord type`` (0 to 83, the arcs run counterclockwise from straight
#            up; the root letter is 0 for A); -1 where the frame has no chord.
#   Made by: ``polar_chords.polar_bars``.
ChordPlaces = npt.NDArray[np.int16]

# BarLengths: how far the bars of each frame reach.
#   Shape: ``(frames,)``: one entry for each frame.
#   Meaning: ``0.5 + 0.5 * the frame's place in the beat``: the length of every bar of the frame as a share of the full
#            radius, from 0.5 to 1.
#   Made by: ``polar_chords.polar_bars``.
BarLengths = npt.NDArray[np.float64]

# PixelNumbers: pixels of the picture, by their flat number.
#   Shape: ``(pixels,)``: the pixels of one arc (or of the part of a neighbour that reaches into it).
#   Meaning: the number of each pixel counted row by row from the top left of the picture (``row * width + column``).
#   Made by: ``polar_chords._geometry``.
PixelNumbers = npt.NDArray[np.intp]

# PixelWeights: how much of each pixel belongs to an arc.
#   Shape: ``(pixels,)``: one entry for each pixel of a ``PixelNumbers``.
#   Meaning: the share of the pixel (0 to 1) that belongs to the arc, so that the sides of a bar are smooth and two bars
#            next to each other have no seam.
#   Made by: ``polar_chords._geometry``.
PixelWeights = npt.NDArray[np.floating]

# CenterDistances: how far each pixel is from the center of the picture.
#   Shape: ``(pixels,)``: one entry for each pixel of a ``PixelNumbers``.
#   Meaning: the distance in pixels from the center of the picture to the middle of the pixel.
#   Made by: ``polar_chords._geometry``.
CenterDistances = npt.NDArray[np.floating]

# BarColors: the color of each bar.
#   Shape: ``(bars, 3)``: one row for each bar being drawn; red, green, blue.
#   Meaning: the color of the bar as floating point numbers from 0 to 255 (a row of the colormap).
#   Made by: ``polar_chords._frame``.
BarColors = npt.NDArray[np.float32]

# Coverage: how much of each pixel the bars of one layer cover.
#   Shape: ``(height * width,)``: one entry for each pixel of the picture, row by row.
#   Meaning: the total share of the pixel (0 or more; 1 is all of it) covered by the bars of the layer.
#   Made by: ``polar_chords._layer``.
Coverage = npt.NDArray[np.float32]

# PremultipliedColors: the colors of the bars of one layer, already multiplied by how much of each pixel they cover.
#   Shape: ``(height * width, 3)``: one row for each pixel of the picture, row by row; red, green, blue.
#   Meaning: the sum over the bars that touch the pixel of ``coverage * color`` (0 to 255 each channel); added to the
#            background times ``1 - coverage``.
#   Made by: ``polar_chords._layer``.
PremultipliedColors = npt.NDArray[np.float32]

# --- Energy Graphs ----------------------------------------------------------------------------------------------------

# RankScores: the rank points that each note scores in each analysis window.
#   Shape: ``(windows, 84)``: one row for each analysis window, one column for each of the 84 drawn notes in note order.
#   Meaning: whole numbers: 84 for the loudest note of the window, 83 for the second loudest and so on down to 1; 0 for
#            a note with no strength and for the notes ranked below it.
#   Made by: ``energy_graphs.rank_scores``.
RankScores = npt.NDArray[np.int64]

# QuasiDecibels: what each note adds to its amplitude total in each analysis window.
#   Shape: ``(windows, 84)``: one row for each analysis window, one column for each of the 84 drawn notes in note order.
#   Meaning: ``20 log10(amplitude) / (20 log10(loudest amplitude of the file))``: 1 for the loudest note of the file,
#            less for fainter notes, never below 0; 0 for a silent note.
#   Made by: ``energy_graphs.quasi_db``.
QuasiDecibels = npt.NDArray[np.float64]

# EnergyTotals: the running totals of a data set of Energy Graphs, in each frame.
#   Shape: ``(frames, 84)``: one row for each frame, one column for each of the 84 drawn notes in note order.
#   Meaning: the sum, over every analysis window that starts before the end of the frame, of the rank points (whole
#            numbers) or of the quasi-decibel values (floating point) of the note: 0 or more, and growing from frame to
#            frame.
#   Made by: ``energy_graphs.frame_energy``.
EnergyTotals = npt.NDArray[np.number]

# BarShares: the share of each note in a data set of Energy Graphs.
#   Shape: ``(rows, 84)``: one row for each frame (or ``(84,)`` for one frame), one column for each of the 84 drawn
#          notes in note order.
#   Meaning: first the softmax of the totals (each row adds up to 1, never 0), then, after ``above_smallest``, the same
#            lowered so that the smallest share of a row is 0: the height of the bar of the note before it is scaled to
#            the picture.
#   Made by: ``energy_graphs.softmax_shares``, ``energy_graphs.above_smallest``.
BarShares = npt.NDArray[np.float64]

# CircleSpeeds: the speed of the four rings of Rhythm Circles at each moment.
#   Shape: ``(moments, 4)``: one row for each moment asked about; the columns are the rings in the same order as
#          ``CircleSeries``.
#   Meaning: revolutions per minute (clockwise positive): the row of ``CircleSeries`` of the latest peak at or before
#            the moment, or the default speeds before the first peak.
#   Made by: ``rhythm_circles.circle_speeds``.
CircleSpeeds = npt.NDArray[np.float64]

# Moments: times of the file to ask about.
#   Shape: ``(moments,)``.
#   Meaning: times in seconds from the start of the file, 0 or more (the middle of each frame is at
#            ``(f + 0.5) / frame rate``).
#   Made by: ``rhythm_circles.rhythm_angles``, ``rhythm_circles._moments``.
Moments = npt.NDArray[np.float64]

# PixelAngles: the direction of each pixel from the center of the picture.
#   Shape: ``(pixels,)``: one entry for each pixel that a ring touches.
#   Meaning: the angle in turns, clockwise from straight up, from 0 (up to 1).
#   Made by: ``rhythm_circles._geometry``.
PixelAngles = npt.NDArray[np.float32]

# ColorList: a list of colors.
#   Shape: ``(n, 3)``: one row for each color (``n`` is stated by each function); red, green, blue.
#   Meaning: each color as floating point numbers from 0 to 255 (rows of the colormap, ready to be blended).
#   Made by: the drawing of each picture (the colors of the rings and of their notches).
ColorList = npt.NDArray[np.float32]

# --- the pictures -----------------------------------------------------------------------------------------------------

# ColorTable: the colors of a colormap.
#   Shape: ``(256, 3)``: one row for each of the 256 steps of the colormap, from its start to its end; the columns are
#          red, green and blue.
#   Meaning: the color of each step, each channel from 0 to 255.
#   Made by: ``colormaps.lookup_table``.
ColorTable = npt.NDArray[np.uint8]

# Pictures: one picture, a frame of the animation.
#   Shape: ``(height, width, 3)``: rows from the top, columns from the left, then red, green and blue (the pictures of
#          the application are 400 rows by 600 columns).
#   Meaning: the color of each pixel, each channel from 0 to 255.
#   Made by: the drawing of each image type (``contour``, ``decay``, ``polar_chords``, ``energy_graphs``,
#            ``chromatic_decay``, ``chromatic_wireframe``, ``rhythm_circles``, ``polychord``).
Pictures = npt.NDArray[np.uint8]
