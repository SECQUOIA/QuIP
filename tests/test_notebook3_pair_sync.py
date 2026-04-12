from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PY_NOTEBOOK = REPO_ROOT / "notebooks_py" / "3-GAMA_python.ipynb"
JL_NOTEBOOK = REPO_ROOT / "notebooks_jl" / "3-GAMA.ipynb"
JL_MANIFEST = REPO_ROOT / "notebooks_jl" / "envs" / "3-GAMA" / "Manifest.toml"


def load_notebook(path: Path) -> dict[str, object]:
    return json.loads(path.read_text())


def notebook_markdown(path: Path) -> str:
    notebook = load_notebook(path)
    return "\n".join(
        "".join(cell.get("source", []))
        for cell in notebook["cells"]
        if cell.get("cell_type") == "markdown"
    )


def notebook_headers(path: Path) -> list[str]:
    notebook = load_notebook(path)
    headers: list[str] = []
    for cell in notebook["cells"]:
        if cell.get("cell_type") != "markdown":
            continue
        for line in "".join(cell.get("source", [])).splitlines():
            if re.match(r"^#{1,6}\s+", line):
                headers.append(line.strip())
    return headers


def manifest_julia_version(path: Path) -> str:
    match = re.search(r'^julia_version = "([^"]+)"', path.read_text(), re.MULTILINE)
    assert match is not None
    return match.group(1)


class Notebook3PairSyncTests(unittest.TestCase):
    def assert_header_subsequence(self, actual: list[str], expected: list[str]) -> None:
        position = 0
        for header in expected:
            try:
                position = actual.index(header, position) + 1
            except ValueError as exc:
                raise AssertionError(f"Missing ordered header {header!r} in {actual!r}") from exc

    def test_python_notebook_follows_the_julia_teaching_flow(self) -> None:
        headers = notebook_headers(PY_NOTEBOOK)
        self.assert_header_subsequence(
            headers,
            [
                "## Graver Augmentation Multiseed Algorithm (Python)",
                "### Introduction to GAMA",
                "### Introduction to Graver basis computation",
                "## Problem statement",
                "### Example",
                "### QUBO formulation for feasible starting points",
                "### References",
            ],
        )

    def test_julia_notebook_uses_the_same_major_sections(self) -> None:
        headers = notebook_headers(JL_NOTEBOOK)
        self.assert_header_subsequence(
            headers,
            [
                "## Graver Augmentation Multiseed Algorithm (Julia)",
                "### Introduction to GAMA",
                "### Introduction to Graver basis computation",
                "## Problem statement",
                "### Example",
                "### QUBO formulation for feasible starting points",
                "### References",
            ],
        )

    def test_python_notebook_has_local_and_colab_setup_context(self) -> None:
        markdown = notebook_markdown(PY_NOTEBOOK)
        self.assertIn("Environment and execution notes", markdown)
        self.assertIn("uv sync --group qubo", markdown)
        self.assertIn("4ti2", markdown)
        self.assertIn("Py4ti2int32", markdown)
        self.assertIn("graver.npy", markdown)

    def test_julia_notebook_keeps_bootstrap_setup_context(self) -> None:
        markdown = notebook_markdown(JL_NOTEBOOK)
        notebook = load_notebook(JL_NOTEBOOK)
        code_text = "\n".join(
            "".join(cell.get("source", []))
            for cell in notebook["cells"]
            if cell.get("cell_type") == "code"
        )

        self.assertIn("Environment setup", markdown)
        self.assertIn("make setup-julia NOTEBOOK=notebooks_jl/3-GAMA.ipynb", markdown)
        self.assertIn('BOOTSTRAP = QuIPNotebookBootstrap.bootstrap_notebook("3-GAMA")', code_text)

    def test_both_notebooks_end_with_the_same_reference_anchor(self) -> None:
        self.assertIn("### References", notebook_markdown(PY_NOTEBOOK))
        self.assertIn("### References", notebook_markdown(JL_NOTEBOOK))
        self.assertIn("QuIPML22", notebook_markdown(PY_NOTEBOOK))
        self.assertIn("QuIPML22", notebook_markdown(JL_NOTEBOOK))

    def test_julia_metadata_matches_the_committed_manifest(self) -> None:
        notebook = load_notebook(JL_NOTEBOOK)
        metadata_version = notebook["metadata"]["language_info"]["version"]
        self.assertEqual(metadata_version, manifest_julia_version(JL_MANIFEST))


if __name__ == "__main__":
    unittest.main()
