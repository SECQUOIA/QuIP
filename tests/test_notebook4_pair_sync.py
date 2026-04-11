from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PY_NOTEBOOK = REPO_ROOT / "notebooks_py" / "4-DWAVE_python.ipynb"
JL_NOTEBOOK = REPO_ROOT / "notebooks_jl" / "4-DWave.ipynb"
JL_MANIFEST = REPO_ROOT / "notebooks_jl" / "envs" / "4-DWave" / "Manifest.toml"


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


class Notebook4PairSyncTests(unittest.TestCase):
    def assert_header_subsequence(self, actual: list[str], expected: list[str]) -> None:
        position = 0
        for header in expected:
            try:
                position = actual.index(header, position) + 1
            except ValueError as exc:
                raise AssertionError(f"Missing ordered header {header!r} in {actual!r}") from exc

    def test_python_notebook_matches_the_julia_section_flow(self) -> None:
        headers = notebook_headers(PY_NOTEBOOK)
        self.assert_header_subsequence(
            headers,
            [
                "## Quantum Annealing via D-Wave (Python)",
                "## Problem statement",
                "### Example",
                "## Now let's solve this using Quantum Annealing!",
                "## References",
            ],
        )

    def test_julia_notebook_uses_the_same_major_sections(self) -> None:
        headers = notebook_headers(JL_NOTEBOOK)
        self.assert_header_subsequence(
            headers,
            [
                "## Quantum Annealing via D-Wave (Julia)",
                "## Problem statement",
                "### Example",
                "## Now let's solve this using Quantum Annealing!",
                "## References",
            ],
        )

    def test_python_notebook_has_local_setup_and_account_guidance(self) -> None:
        markdown = notebook_markdown(PY_NOTEBOOK)
        self.assertIn("Environment and execution notes", markdown)
        self.assertIn("uv sync --group qubo", markdown)
        self.assertIn("dwave setup", markdown)
        self.assertIn("dwave ping", markdown)
        self.assertIn("DWaveSampler()", markdown)

    def test_julia_notebook_keeps_bootstrap_and_token_guidance(self) -> None:
        markdown = notebook_markdown(JL_NOTEBOOK)
        code_text = "\n".join(
            "".join(cell.get("source", []))
            for cell in load_notebook(JL_NOTEBOOK)["cells"]
            if cell.get("cell_type") == "code"
        )

        self.assertIn("Environment setup", markdown)
        self.assertIn("make setup-julia NOTEBOOK=notebooks_jl/4-DWave.ipynb", markdown)
        self.assertIn("DWAVE_API_TOKEN", markdown)
        self.assertIn("DWaveSampler", code_text)

    def test_problem_statement_notation_is_aligned(self) -> None:
        python_markdown = notebook_markdown(PY_NOTEBOOK)
        julia_markdown = notebook_markdown(JL_NOTEBOOK)

        self.assertIn(r"\mathbf{Q}", python_markdown)
        self.assertIn(r"\mathbf{Q}", julia_markdown)
        self.assertIn(r"\beta", python_markdown)
        self.assertIn(r"\beta", julia_markdown)
        self.assertIn("weighted adjacency matrix", python_markdown)
        self.assertIn("weighted adjacency matrix", julia_markdown)

    def test_both_notebooks_end_with_the_same_reference_anchor(self) -> None:
        self.assertIn("## References", notebook_markdown(PY_NOTEBOOK))
        self.assertIn("## References", notebook_markdown(JL_NOTEBOOK))
        self.assertIn("QuIPML22", notebook_markdown(PY_NOTEBOOK))
        self.assertIn("QuIPML22", notebook_markdown(JL_NOTEBOOK))

    def test_julia_metadata_matches_the_committed_manifest(self) -> None:
        notebook = load_notebook(JL_NOTEBOOK)
        metadata_version = notebook["metadata"]["language_info"]["version"]
        self.assertEqual(metadata_version, manifest_julia_version(JL_MANIFEST))


if __name__ == "__main__":
    unittest.main()
