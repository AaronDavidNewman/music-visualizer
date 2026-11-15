"""The kinds of picture a frame can be drawn as.

``contour`` is the grid of note values (12 x 7) drawn as a filled contour map. It is drawn by ``contour.py``, because it
needs matplotlib's drawing; this module stays pure Python and only lists its name. ``decay`` has a circle for each of
the 84 notes on the 12 x 7 grid (``note_grid.py``), each one flat disc that keeps points from frame to frame, charged by
the loudest notes and spreading into its neighbours as time passes (``decay.py``). ``decay-exp`` is ``decay`` with the
points gained and lost along an exponential curve (``decay_exp.py``). ``polar-chords`` is a polar bar graph of the
loudest notes (clockwise) and the chord of the frame (counterclockwise) (``polar_chords.py``). ``energy-graphs`` is a
running histogram of the 84 notes with two data sets, which notes have been loudest (rank points) and their accumulated
amplitude (quasi-decibels), each softmaxed (``energy_graphs.py``). ``chromatic-decay`` is ``decay-exp`` for the 12
chromatic tones only: 12 circles on a ring in circle-of-fifths order, charged by the loudest octave of each letter,
whose points decay to the letters 5 and 7 above (``chromatic_decay.py``). ``rhythm-circles`` is four concentric notched
rings that turn with the current tempo found from the local peaks, the tempo of the latest peak and the rates of change
of both (``rhythm_circles.py``). ``chromatic-wireframe`` draws the points of ``chromatic-decay`` as a ridge plot in
three dimensions: one line for each frame across the 12 letters, the newest in front, each in the color of its place in
the beat (``chromatic_wireframe.py``). (Tiles, blended tiles, circles, circles paint and concentric, the first five
kinds of picture, were removed in feature 040.)

No data processing: this module only holds the names of the eight kinds of picture (``IMAGE_TYPES``), the default and
the check of a name; the map of how each kind is made from an uploaded file is the pipeline overview below.

Pipeline overview:
    How a job makes the frames of every image type, in order (``routers/jobs.py`` ``create_job()`` and
    ``frame_rendering.write_frames()``). The first steps are the same for every type; MEASURE is done only by the types
    marked below; DRAW is each type's own. Each step names the function and the data after it (the names of the arrays
    are in ``array_types.py``; ``windows`` are the analysis windows of the audio, ``frames`` the pictures of the
    animation, which is 10 to 60 a second).

    READ     - ``note_analysis.read_wav()`` - two ``RawSamples`` ``(samples,)`` (left and right channel) and the file's
    sample rate. ANALYZE  - ``note_analysis.analyze_channels()`` - ``NoteStrengths`` ``(windows, 88)``: the strength of
    each of the 88 notes in each analysis window. FLOOR    - ``noise_floor.floor_analysis()`` - ``NoteStrengths``
    ``(windows, 88)``: a strength below a thousandth of the loudest of the file is 0. MEASURE  - only for some types,
    one of three measurements (all use the two channels of the file or the analysis, never the picture):
               * BEAT: ``local_peaks.measure_local_peaks()`` then ``LocalPeaks.frame_positions()`` - ``BeatPositions``
                 ``(frames,)``: the place of each frame in the local energy peak, 0 to 1. Done before AVERAGE.
               * RHYTHM: ``local_peaks.measure_local_peaks()`` then ``rhythm_circles.rhythm_angles()`` (which asks
                 ``tempo_finder.find_tempo()`` for the current tempo) - ``CircleAngles`` ``(frames, 4)``: the angle of
                 each ring in each frame. Done before AVERAGE.
               * ENERGY: ``energy_graphs.frame_energy()`` - two ``EnergyTotals`` ``(frames, 84)``: the running rank
                 points and quasi-decibel values of each note. Made in the same call as AVERAGE, right after it.
    AVERAGE  - ``frame_rendering.average_frames()`` - ``NoteStrengths`` ``(frames, 88)``: the mean of the windows each
    frame owns. SMOOTH   - ``frame_rendering.smooth_frames()`` - ``NoteStrengths`` ``(frames, 88)``: each frame mixed
    with the frames before it. Done for every type; Energy Graphs and
               Rhythm Circles draw from their measurement and do not use these values.
    DRAW     - the type's own stages (below) - ``Pictures`` ``(height, width, 3)`` for each frame, 400 rows by 600
    columns. SAVE     - each picture is written as ``frame_<index>.png`` (a few threads, ``frame_saving.SAVE_WORKERS``)
    and ``render.json`` records the frame rate; the job answers with
               the settings used and the address of the frames.

    contour (default) - MEASURE: BEAT only when Beat coloring is on, else none. Settings that apply: Threshold, Notes,
    Oversampling, Interpolate, Gaussian smoothing, Wave count.
      DRAW: 1. ``note_selection.spread_notes()`` (Notes) - ``NoteStrengths`` ``(frames, 84)``: only the loudest notes of
      the file, spread over the 84 places.
            2. ``resolution.interpolate_grid()`` (Oversampling) - ``GridValues`` ``(frames, 7r * 12r)``: the grid made
               finer.
            3. ``frame_rendering.hidden_below()`` (Threshold) - faint values set to 0.
            4. ``frame_interpolation.key_frames()`` (Interpolate) - which frames are drawn from the music.
            5. ``contour.write_contour_frames()`` - for each drawn frame: ``FrameGrid`` ``(7r, 12r)``,
               ``contour.directionalSmoothing()``, with a beat above 0 multiplied by ``beat_wave.wave_modifier()``, then
               ``contourf``: ``Pictures``.
            6. ``gaussian.blur_frames()`` (Gaussian smoothing) - the drawn frames blurred.
            7. ``frame_interpolation.write_interpolated_frames()`` - the in-between frames made from their drawn
               neighbours.
    decay - MEASURE: BEAT. Settings that apply: Decay rate, the four decay amounts, Note layout.
      DRAW: 1. ``decay.circle_points()`` - ``CirclePoints`` ``(frames, 84)``: it first asks ``decay.gains()`` for
      ``PointGains`` ``(frames, 84)`` (the five loudest notes of each
               frame gain 24, 20, 16, 12 and 8 points plus the beat bonus) and ``note_layout.arrange_notes()`` (Note
               layout) to put them in cell order, then for each frame adds the gains and calls ``decay.decay_step()`` as
               often as the decay rate says.
            2. ``decay.write_decay_frames()`` - ``decay._geometry()`` once, then ``decay._frame()`` for each frame:
               ``Pictures``.
    decay-exp - MEASURE: BEAT. Settings that apply: Decay rate, Note layout (the decay amounts are not used).
      DRAW: as decay, with 1. ``decay_exp.circle_points()`` (which runs ``decay_exp._simulate()``: the gains of
      ``decay.gains()`` each cut to ``g * exp(-g / taper)``, then
            ``decay_exp.decay_exp_step()``, in which a circle gives ``sin(pi / 2 * p / 64) ** 2`` to each neighbour per
            frame, and at the end of each frame the taper of the next one from ``decay_exp.next_taper()``, moving
            between 8 and 12); the drawing is ``decay.write_decay_frames()``.
    polar-chords - MEASURE: BEAT. Settings that apply: Notes shown, Note layout.
      DRAW: 1. ``polar_chords.polar_bars()`` - the arc of each of the loudest notes (``BarArcs`` ``(frames, count)``),
      made to follow their notes one arc a frame
               (``polar_chords.follow_arcs()``), the bars of a quieter volume hidden when in the arc of a louder one.
            2. ``chords.measure_chords()`` - the chord of each frame: ``ChordPlaces`` ``(frames,)``.
            3. ``polar_chords.write_polar_frames()`` - ``polar_chords._geometry()`` once, then ``polar_chords._frame()``
               for each frame: ``Pictures``.
    energy-graphs - MEASURE: ENERGY (no beat). Settings that apply: none (only the colormap).
      DRAW: ``energy_graphs.write_energy_frames()`` - makes the background once, turns each data set into bars with
      ``energy_graphs.softmax_shares()`` then
            ``energy_graphs.above_smallest()`` (``BarShares`` ``(frames, 84)``), then ``energy_graphs._frame()`` for
            each frame: ``Pictures``.
    chromatic-decay - MEASURE: BEAT. Settings that apply: Threshold, Decay rate (whole numbers 1 to 10).
      DRAW: 1. ``chromatic_decay.circle_points()`` - ``CirclePoints`` ``(frames, 12)``:
      ``chromatic_decay.apply_threshold()``, then the gains (``chromatic_decay._raw_gains()``,
               which uses ``chromatic_decay.letter_energies()``: ``LetterEnergies`` ``(frames, 12)``), then for each
               frame the cut gains and ``chromatic_decay.chromatic_step()``.
            2. ``chromatic_decay.write_chromatic_frames()`` - the target of the beat (``ring_levels()``,
               ``ring_colors_of()``), then ``chromatic_decay._frame()`` for each frame: the 12 circles on a ring in
               circle-of-fifths order: ``Pictures``.
    rhythm-circles - MEASURE: RHYTHM (no beat). Settings that apply: none (only the colormap).
      DRAW: ``rhythm_circles.write_rhythm_frames()`` - ``rhythm_circles.ring_colors_rows()`` and
      ``rhythm_circles._geometry()`` once, then ``rhythm_circles._frame()`` for each
            frame: four rings with a notch turned by ``CircleAngles``: ``Pictures``.
    chromatic-wireframe - MEASURE: BEAT. Settings that apply: Threshold, Decay rate (whole numbers 1 to 10).
      DRAW: 1. ``chromatic_decay.circle_points()`` - as chromatic-decay: ``CirclePoints`` ``(frames, 12)``.
            2. ``chromatic_wireframe.write_wireframe_frames()`` - ``chromatic_wireframe.line_colors()`` (``LineColors``
               ``(frames, 3)``), the line of each frame (``chromatic_wireframe.line_heights()``, which uses
               ``line_sums()`` and ``line_angles()``: ``LineHeights`` ``(frames, n)``), then
               ``chromatic_wireframe._frame()`` for each frame: the lines of the frame and the frames before it, oldest
               first: ``Pictures``.

    When an image type is added or changed, its block here is changed in the same piece of work.

This module knows nothing about the note analysis or the grid of the application.
"""

IMAGE_TYPES = ("contour", "decay", "decay-exp", "polar-chords", "energy-graphs", "chromatic-decay", "rhythm-circles", "chromatic-wireframe")
DEFAULT_IMAGE_TYPE = "contour"


def check_image_type(value: object) -> str:
    """Return ``value`` when it is exactly one of the offered names (no trimming, no case folding)."""
    if not isinstance(value, str) or value not in IMAGE_TYPES:
        raise ValueError(f"The image type must be one of {', '.join(IMAGE_TYPES)}.")
    return value
