"""The layers' import rules (see AGENTS.md). Fix the code, not this test."""

import ast
from pathlib import Path

import pytest

APP = Path(__file__).parent.parent / "app"

FORBIDDEN = {
    "domain": ("app.application", "app.infrastructure", "app.presentation"),
    "application": ("app.infrastructure", "app.presentation", "app.bootstrap"),
    "infrastructure": ("app.presentation", "app.bootstrap"),
    "presentation": ("app.infrastructure",),
}
# frameworks stay out of the inner layers
FORBIDDEN_LIBRARIES = {
    "domain": ("fastapi", "pydantic", "aio_pika", "aiormq", "smtplib"),
    "application": ("fastapi", "pydantic", "aio_pika", "aiormq", "smtplib"),
}


def imports(path: Path) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


@pytest.mark.parametrize("layer", sorted(FORBIDDEN))
def test_layer_imports(layer: str) -> None:
    banned = FORBIDDEN[layer] + FORBIDDEN_LIBRARIES.get(layer, ())
    for path in (APP / layer).rglob("*.py"):
        for name in imports(path):
            assert not name.startswith(banned), f"{path} imports {name}"
