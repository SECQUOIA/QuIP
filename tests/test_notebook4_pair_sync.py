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


def notebook_code(path: Path) -> str:
    notebook = load_notebook(path)
    return "\n".join(
        "".join(cell.get("source", []))
        for cell in notebook["cells"]
        if cell.get("cell_type") == "code"
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


def manifest_dwave_version(path: Path) -> tuple[int, int, int]:
    manifest = path.read_text()
    match = re.search(
        r'\[\[deps\.DWave\]\].*?version = "(\d+)\.(\d+)\.(\d+)"',
        manifest,
        re.S,
    )
    assert match is not None
    return tuple(int(match.group(i)) for i in (1, 2, 3))


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
        self.assertIn("uv run --group qubo dwave setup", markdown)
        self.assertIn("uv run --group qubo dwave ping", markdown)
        self.assertIn("dwave setup", markdown)
        self.assertIn("dwave ping", markdown)
        self.assertIn("DWaveSampler()", markdown)

    def test_julia_notebook_keeps_bootstrap_and_token_guidance(self) -> None:
        markdown = notebook_markdown(JL_NOTEBOOK)
        code_text = notebook_code(JL_NOTEBOOK)

        self.assertIn("Environment setup", markdown)
        self.assertIn("make setup-julia NOTEBOOK=notebooks_jl/4-DWave.ipynb", markdown)
        self.assertIn("DWave.jl", markdown)
        self.assertIn("https://github.com/JuliaQUBO/DWave.jl", markdown)
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

    def test_python_offset_code_uses_the_same_beta_notation(self) -> None:
        code_text = notebook_code(PY_NOTEBOOK)

        self.assertIn("beta = rho*np.matmul(b.T,b)", code_text)
        self.assertIn("offset=beta", code_text)
        self.assertNotIn("cQ", code_text)

    def test_both_notebooks_end_with_the_same_reference_anchor(self) -> None:
        python_markdown = notebook_markdown(PY_NOTEBOOK)
        julia_markdown = notebook_markdown(JL_NOTEBOOK)

        self.assertIn("## References", python_markdown)
        self.assertIn("## References", julia_markdown)
        for shared_reference in [
            "QuIPML22",
            "D-Wave Ocean SDK documentation",
        ]:
            self.assertIn(shared_reference, python_markdown)
            self.assertIn(shared_reference, julia_markdown)
        self.assertIn("dimod", python_markdown)
        self.assertIn("dwave-samplers", python_markdown)
        self.assertIn("NetworkX", python_markdown)
        self.assertIn("DWave.jl", julia_markdown)
        self.assertIn("JuMP", julia_markdown)
        self.assertIn("Graphs.jl", julia_markdown)

    def test_python_notebook_uses_current_dwave_sampler_import(self) -> None:
        code_text = notebook_code(PY_NOTEBOOK)

        self.assertIn("from dwave.samplers import SimulatedAnnealingSampler", code_text)
        self.assertIn("simAnnSampler = SimulatedAnnealingSampler()", code_text)
        self.assertNotIn("import neal", code_text)
        self.assertNotIn("neal.SimulatedAnnealingSampler()", code_text)

    def test_julia_metadata_matches_the_committed_manifest(self) -> None:
        notebook = load_notebook(JL_NOTEBOOK)
        metadata_version = notebook["metadata"]["language_info"]["version"]
        self.assertEqual(metadata_version, manifest_julia_version(JL_MANIFEST))

    def test_julia_manifest_uses_current_released_dwavel(self) -> None:
        manifest = JL_MANIFEST.read_text()
        self.assertGreaterEqual(manifest_dwave_version(JL_MANIFEST), (0, 6, 3))
        self.assertNotIn("repo-rev", manifest.split("[[deps.DWave]]")[1].split("[[")[0])


if __name__ == "__main__":
    unittest.main()
