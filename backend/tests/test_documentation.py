"""The presence check of the documentation standard (feature 041): what a program can tell about the other two kinds of documentation.

The rules are in ``.specify/memory/constitution.md`` (principles II and III) and ``specs/041-code-readability-docs/contracts/documentation-standard.md``; what this file checks is
in ``specs/041-code-readability-docs/contracts/checks.md``. It parses the files of ``backend/app`` with ``ast`` and never imports them. It can tell that something is *there*
(an "Order of operations" list, an array named in its docstring, a description of each kind of array); it cannot tell whether it is *true*, which is reviewed with the two tools
of the feature folder (``tools/shape_probe.py``, ``tools/trace_pipeline.py``).

A module of ``backend/app`` that has a function or a class must be put in exactly one of the two sets below, so a new module fails until someone decides which kind it is.
"""

import ast
import re
from pathlib import Path

from app.services.image_types import IMAGE_TYPES

APP = Path(__file__).resolve().parents[1] / "app"
ARRAY_TYPES = APP / "services" / "array_types.py"

# Modules that transform data: their module docstring has an "Order of operations:" numbered list.
PROCESSING_MODULES = {
    "services/beat_wave.py",
    "services/chords.py",
    "services/chromatic_decay.py",
    "services/chromatic_wireframe.py",
    "services/colormaps.py",
    "services/contour.py",
    "services/decay.py",
    "services/decay_exp.py",
    "services/energy_graphs.py",
    "services/frame_interpolation.py",
    "services/frame_rendering.py",
    "services/image_processing.py",
    "services/gaussian.py",
    "services/local_peaks.py",
    "services/noise_floor.py",
    "services/note_analysis.py",
    "services/note_grid.py",
    "services/note_layout.py",
    "services/note_selection.py",
    "services/polar_chords.py",
    "services/resolution.py",
    "services/rhythm_circles.py",
    "services/tempo_finder.py",
    "services/window_spacing.py",
    "services/video.py",
    "routers/jobs.py",
}

# Modules that hold constants, settings, names or routing only: their module docstring says "No data processing:" and what they hold.
EXEMPT_MODULES = {
    "config.py",
    "main.py",
    "routers/hello.py",
    "routers/images.py",
    "routers/video.py",
    "services/array_types.py",
    "services/frame_saving.py",
    "services/image_types.py",
}

SHARED_STEPS = ("READ", "ANALYZE", "FLOOR", "MEASURE", "AVERAGE", "SMOOTH", "DRAW", "SAVE")


def python_files() -> list[Path]:
    return sorted(p for p in APP.rglob("*.py") if "__pycache__" not in p.parts)


def relative(path: Path) -> str:
    return path.relative_to(APP).as_posix()


def parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def alias_names() -> list[str]:
    """The names defined in ``array_types.py`` (the module-level assignments)."""
    return [t.id for node in parse(ARRAY_TYPES).body if isinstance(node, ast.Assign) for t in node.targets if isinstance(t, ast.Name)]


def array_pattern() -> re.Pattern[str]:
    names = "|".join(re.escape(n) for n in alias_names())
    return re.compile(rf"\b({names}|ndarray|NDArray)\b")


def is_array(annotation: ast.AST | None, pattern: re.Pattern[str]) -> bool:
    return annotation is not None and pattern.search(ast.unparse(annotation)) is not None


def top_level_functions(tree: ast.Module) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    """The functions of the module and the methods of its classes (not the functions nested inside functions)."""
    found: list[ast.FunctionDef | ast.AsyncFunctionDef] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            found.append(node)
        elif isinstance(node, ast.ClassDef):
            found += [n for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    return found


def has_code(tree: ast.Module) -> bool:
    return any(isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) for node in tree.body)


# --- 1. every module is placed, and says its order of operations (or that it has none) ----------------------------------------------


def test_the_two_lists_of_modules_do_not_overlap_and_name_real_files():
    files = {relative(p) for p in python_files()}
    assert not (PROCESSING_MODULES & EXEMPT_MODULES), f"in both lists: {sorted(PROCESSING_MODULES & EXEMPT_MODULES)}"
    missing = sorted((PROCESSING_MODULES | EXEMPT_MODULES) - files)
    assert not missing, f"named in a list but there is no such file: {missing}"


def test_every_module_with_code_is_placed_in_one_of_the_two_lists():
    placed = PROCESSING_MODULES | EXEMPT_MODULES
    unplaced = [relative(p) for p in python_files() if has_code(parse(p)) and relative(p) not in placed]
    assert not unplaced, "modules with code that are in neither list (a processing module needs 'Order of operations:', the others 'No data processing:'): " + ", ".join(unplaced)


def test_every_processing_module_starts_with_its_order_of_operations():
    problems = []
    for name in sorted(PROCESSING_MODULES):
        doc = ast.get_docstring(parse(APP / name)) or ""
        match = re.search(r"^[ \t]*Order of operations:[ \t]*\n(?:[ \t]*\n)*[ \t]*1\. ", doc, re.MULTILINE)
        if not match:
            problems.append(f"{name}: module docstring has no 'Order of operations:' followed by a numbered list starting at 1. (documentation-standard.md section 3)")
    assert not problems, "\n".join(problems)


def test_every_module_without_data_processing_says_so():
    problems = []
    for name in sorted(EXEMPT_MODULES):
        doc = ast.get_docstring(parse(APP / name)) or ""
        if "No data processing:" not in doc:
            problems.append(f"{name}: module docstring has no 'No data processing: ...' line (documentation-standard.md section 3)")
    assert not problems, "\n".join(problems)


# --- 2. every array is named in the docstring of its function --------------------------------------------------------------------


def test_every_function_that_takes_or_returns_an_array_documents_it():
    pattern = array_pattern()
    problems = []
    for path in python_files():
        if path == ARRAY_TYPES:
            continue
        for function in top_level_functions(parse(path)):
            arguments = function.args
            parameters = arguments.posonlyargs + arguments.args + arguments.kwonlyargs + ([arguments.vararg] if arguments.vararg else []) + ([arguments.kwarg] if arguments.kwarg else [])
            array_parameters = [a.arg for a in parameters if is_array(a.annotation, pattern)]
            returns_array = is_array(function.returns, pattern)
            if not array_parameters and not returns_array:
                continue
            where = f"{relative(path)}:{function.lineno} {function.name}"
            doc = ast.get_docstring(function)
            if not doc:
                problems.append(f"{where}: takes or returns an array but has no docstring (documentation-standard.md section 2)")
                continue
            for name in array_parameters:
                if f"``{name}``" not in doc:
                    problems.append(f"{where}: array parameter ``{name}`` is not named in the docstring (documentation-standard.md section 2)")
            if returns_array and "Returns:" not in doc:
                problems.append(f"{where}: returns an array but the docstring has no 'Returns:' line (documentation-standard.md section 2)")
    assert not problems, f"{len(problems)} array(s) not documented:\n" + "\n".join(problems)


def test_every_data_class_with_array_fields_documents_each_one():
    pattern = array_pattern()
    problems = []
    for path in python_files():
        for node in parse(path).body:
            if not isinstance(node, ast.ClassDef) or not any("dataclass" in ast.unparse(d) for d in node.decorator_list):
                continue
            fields = [n.target.id for n in node.body if isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name) and is_array(n.annotation, pattern)]
            if not fields:
                continue
            doc = ast.get_docstring(node) or ""
            if "Attributes:" not in doc:
                problems.append(f"{relative(path)}:{node.lineno} class {node.name}: has array fields ({', '.join(fields)}) but no 'Attributes:' block in its docstring")
                continue
            problems += [f"{relative(path)}:{node.lineno} class {node.name}: array field ``{f}`` is not named in the docstring" for f in fields if f"``{f}``" not in doc]
    assert not problems, "\n".join(problems)


# --- 3. every kind of array has one description ----------------------------------------------------------------------------------


def test_every_alias_in_array_types_has_a_description_with_shape_meaning_and_origin():
    lines = ARRAY_TYPES.read_text(encoding="utf-8").split("\n")
    problems = []
    for node in parse(ARRAY_TYPES).body:
        if not isinstance(node, ast.Assign):
            continue
        name = node.targets[0].id
        block = []
        i = node.lineno - 2  # the lines just above the assignment
        while i >= 0 and lines[i].lstrip().startswith("#"):
            block.append(lines[i])
            i -= 1
        text = "\n".join(reversed(block))
        for word in (f"# {name}:", "Shape:", "Meaning:", "Made by:"):
            if word not in text:
                problems.append(f"array_types.py:{node.lineno} {name}: the comment above has no '{word}'")
    assert not problems, "\n".join(problems)


def test_every_alias_that_is_used_is_defined_in_array_types():
    defined = set(alias_names())
    problems = []
    for path in python_files():
        if path == ARRAY_TYPES:
            continue
        for node in ast.walk(parse(path)):
            if isinstance(node, ast.ImportFrom) and node.module and node.module.endswith("array_types"):
                problems += [f"{relative(path)}: imports {a.name} from array_types, which does not define it" for a in node.names if a.name not in defined]
    assert not problems, "\n".join(problems)


# --- 4. the overview of the image types -----------------------------------------------------------------------------------------


def test_the_overview_of_the_image_types_names_every_type_and_every_shared_step():
    doc = ast.get_docstring(parse(APP / "services" / "image_types.py")) or ""
    assert "Pipeline overview:" in doc, "image_types.py: the module docstring has no 'Pipeline overview:' (documentation-standard.md section 4)"
    overview = doc[doc.index("Pipeline overview:") :]
    missing_types = [t for t in IMAGE_TYPES if t not in overview]
    missing_steps = [s for s in SHARED_STEPS if s not in overview]
    assert not missing_types, f"the overview does not name the image type(s): {missing_types}"
    assert not missing_steps, f"the overview does not name the shared step(s): {missing_steps}"
