"""An independent reader of the OBJ files of feature 045, written from data-model.md and not from the writer.

``read_obj(text)`` returns ``(vertices, faces, names)``:

* ``vertices``: one tuple of 6 floats (x, y, z, r, g, b) for each ``v`` line;
* ``faces``: one tuple of 4 ints for each ``f`` line, each from 1 to the number of vertices;
* ``names``: the ``o`` lines' names (a list) - the ``#`` comment lines are skipped.

It raises ``ValueError`` for anything else: a ``v`` line without exactly 6 numbers, an ``f`` line without exactly 4
whole numbers, a face number outside the vertices, a number written with an exponent or with a comma, or any other
keyword. Only plain Python is used.
"""

import re

_NUMBER = re.compile(r"^-?\d+\.\d{4}$")


def read_obj(text: str) -> tuple[list[tuple[float, ...]], list[tuple[int, ...]], list[str]]:
    vertices: list[tuple[float, ...]] = []
    faces: list[tuple[int, ...]] = []
    names: list[str] = []
    if "\r" in text:
        raise ValueError("The line ends must be \\n.")
    for number, line in enumerate(text.split("\n"), start=1):
        if not line or line.startswith("#"):
            continue
        keyword, *fields = line.split(" ")
        if keyword == "o":
            names.append(" ".join(fields))
        elif keyword == "v":
            if len(fields) != 6:
                raise ValueError(f"Line {number}: a vertex needs 6 numbers, not {len(fields)}.")
            for field in fields:
                if not _NUMBER.fullmatch(field):
                    raise ValueError(f"Line {number}: {field!r} is not a number with 4 decimals.")
            vertices.append(tuple(float(field) for field in fields))
        elif keyword == "f":
            if len(fields) != 4 or not all(field.isdigit() for field in fields):
                raise ValueError(f"Line {number}: a face needs 4 whole numbers.")
            faces.append(tuple(int(field) for field in fields))
        else:
            raise ValueError(f"Line {number}: unknown keyword {keyword!r}.")
    for face in faces:
        if min(face) < 1 or max(face) > len(vertices):
            raise ValueError(f"The face {face} refers to a vertex that does not exist (there are {len(vertices)}).")
    return vertices, faces, names
