"""The scan for missing types (feature 041): every function of ``backend/app`` has a type on every parameter and on its return value.

The rule is in ``.specify/memory/constitution.md`` (principle I) and in ``specs/041-code-readability-docs/contracts/documentation-standard.md``; what this test checks is in
``specs/041-code-readability-docs/contracts/checks.md``. It parses the files with ``ast`` and never imports them, so it is fast and cannot be broken by the application's
own imports. There is no list of exceptions: a function added without types fails it.
"""

import ast
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "app"
UNTYPED_SELF = ("self", "cls")


def python_files() -> list[Path]:
    return sorted(p for p in APP.rglob("*.py") if "__pycache__" not in p.parts)


def functions_of(tree: ast.AST) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    """Every function and method of a module, nested ones included (lambdas cannot be annotated and are not functions of this check)."""
    return [node for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]


def parameters_of(function: ast.FunctionDef | ast.AsyncFunctionDef) -> list[ast.arg]:
    arguments = function.args
    found = arguments.posonlyargs + arguments.args + arguments.kwonlyargs
    if arguments.vararg:
        found.append(arguments.vararg)
    if arguments.kwarg:
        found.append(arguments.kwarg)
    return found


def problems_in(path: Path) -> tuple[int, list[str]]:
    """The number of functions of the file and one message for each function that lacks a type on a parameter or on its return value."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    relative = path.relative_to(APP.parent.parent).as_posix()
    functions = functions_of(tree)
    messages = []
    for function in sorted(functions, key=lambda f: f.lineno):
        untyped = [a.arg for a in parameters_of(function) if a.annotation is None and a.arg not in UNTYPED_SELF]
        if untyped:
            messages.append(f"{relative}:{function.lineno} {function.name}: parameter(s) without a type: {', '.join(untyped)}")
        if function.returns is None:
            messages.append(f"{relative}:{function.lineno} {function.name}: no return type (use -> None when nothing is returned)")
    return len(functions), messages


def test_the_scan_sees_the_whole_backend():
    files = python_files()
    counts = [problems_in(path)[0] for path in files]
    assert len(files) > 25, "the scan found too few files: is the path of backend/app right?"
    assert sum(counts) > 200, "the scan found too few functions: is it looking at the right files?"
    assert sum(1 for c in counts if c) > 25


def test_every_function_of_the_backend_has_a_type_on_every_parameter_and_on_its_return_value():
    messages = []
    for path in python_files():
        messages += problems_in(path)[1]
    assert not messages, f"{len(messages)} missing type(s) in backend/app:\n" + "\n".join(messages)


def test_the_scan_itself_finds_a_missing_type(tmp_path):
    """The scan is not vacuous: it reports an untyped parameter, an untyped return, a nested function and a method, and accepts a typed one."""
    sample = tmp_path / "app" / "sample.py"
    sample.parent.mkdir()
    sample.write_text(
        "def typed(a: int, *rest: int, key: str = 'x', **more: int) -> None:\n    pass\n\n"
        "def untyped_parameter(a, b: int) -> int:\n    return b\n\n"
        "def untyped_return(a: int):\n    return a\n\n"
        "def outer(a: int) -> int:\n    def inner(x):\n        return x\n    return inner(a)\n\n"
        "class C:\n    def method(self, value) -> None:\n        pass\n    @classmethod\n    def make(cls, value: int) -> 'C':\n        return cls()\n",
        encoding="utf-8",
    )
    tree = ast.parse(sample.read_text(encoding="utf-8"))
    found = {}
    for function in functions_of(tree):
        untyped = [a.arg for a in parameters_of(function) if a.annotation is None and a.arg not in UNTYPED_SELF]
        found[function.name] = (untyped, function.returns is None)
    assert found["typed"] == ([], False)
    assert found["untyped_parameter"] == (["a"], False)
    assert found["untyped_return"] == ([], True)
    assert found["inner"] == (["x"], True)
    assert found["method"] == (["value"], False)
    assert found["make"] == ([], False)
