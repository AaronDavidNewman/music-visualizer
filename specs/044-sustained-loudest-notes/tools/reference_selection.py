"""An independent, plain-Python version of the held-notes rule of feature 044, for the tests.

It is written from ``specs/044-sustained-loudest-notes/spec.md`` and not from ``backend/app/services/held_notes.py``, so that the two can disagree. It uses lists and loops only (no NumPy in the
algorithm), one frame at a time.

Arrays (as lists):
    * ``values``: ``(frames, notes)`` - the strength of each note in each frame, each frame a list of numbers that are not negative (``NoteStrengths`` with 84 or 12 columns).
    * the result: ``(frames, places)`` with ``places`` between 0 and ``count`` - for each frame the indices of the notes of its selection, loudest first, only notes that sound (a value above 0).
      Unlike ``LoudestIndices`` it is not padded.
"""


def reference_selection(values: list[list[float]], count: int, extra: int) -> list[list[int]]:
    """The selection of every frame: the notes that are held and the loudest notes that are not held, at most ``count`` of them, loudest first.

    A note is *held* when it was in the selection of the frame before and is among the loudest ``count + extra`` of this frame (rank 1 is the loudest; equal strengths: the lower note is louder) and
    its strength is above 0. A free place (fewer than ``count`` held notes) goes to the loudest notes that are not held and sound. The first frame, and any frame after a frame with an empty
    selection, has nothing held.
    """
    result: list[list[int]] = []
    previous: list[int] = []
    for row in values:
        ranked = sorted(range(len(row)), key=lambda note: (-row[note], note))
        rank = {note: place for place, note in enumerate(ranked)}  # 0 is the loudest
        held = [note for note in previous if rank[note] < count + extra and row[note] > 0]
        selected = list(held)
        for note in ranked:
            if len(selected) >= count:
                break
            if row[note] > 0 and note not in selected:
                selected.append(note)
        selected.sort(key=lambda note: rank[note])
        result.append(selected)
        previous = selected
    return result
