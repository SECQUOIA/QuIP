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
        self.assertIn("Py4ti2int32", markdown)
        self.assertIn("graver.npy", markdown)
        self.assertIn("falls back to the bundled `graver.npy` file", markdown)

    def test_julia_notebook_keeps_bootstrap_setup_context(self) -> None:
        markdown = notebook_markdown(JL_NOTEBOOK)
        code_text = notebook_code(JL_NOTEBOOK)

        self.assertIn("Environment setup", markdown)
        self.assertIn("make setup-julia NOTEBOOK=notebooks_jl/3-GAMA.ipynb", markdown)
        self.assertIn('BOOTSTRAP = QuIPNotebookBootstrap.bootstrap_notebook("3-GAMA")', code_text)

    def test_both_notebooks_end_with_the_same_reference_anchor(self) -> None:
        self.assertIn("### References", notebook_markdown(PY_NOTEBOOK))
        self.assertIn("### References", notebook_markdown(JL_NOTEBOOK))
        self.assertIn("QuIPML22", notebook_markdown(PY_NOTEBOOK))
        self.assertIn("QuIPML22", notebook_markdown(JL_NOTEBOOK))
        self.assertIn("1902.04215", notebook_markdown(PY_NOTEBOOK))
        self.assertIn("1907.10930", notebook_markdown(PY_NOTEBOOK))
        self.assertIn("1902.04215", notebook_markdown(JL_NOTEBOOK))
        self.assertIn("1907.10930", notebook_markdown(JL_NOTEBOOK))
        self.assertNotIn("proposed by [two]", notebook_markdown(PY_NOTEBOOK))
        self.assertNotIn("proposed by [two]", notebook_markdown(JL_NOTEBOOK))

    def test_both_notebooks_share_the_same_core_narrative_anchors(self) -> None:
        py_markdown = notebook_markdown(PY_NOTEBOOK)
        jl_markdown = notebook_markdown(JL_NOTEBOOK)

        for anchor in [
            "First we would write this problem as an unconstrained one by penalizing the linear constraints as quadratics in the objective.",
            "Now we can highlight another feature of the algorithm, computing starting feasible solutions.",
            "We use simulated annealing here because the goal is not a single feasible point but a diverse set of feasible starts.",
            "The Graver basis of this matrix $A$ has 29789 elements",
        ]:
            self.assertIn(anchor, py_markdown)
            self.assertIn(anchor, jl_markdown)

    def test_julia_notebook_uses_the_same_unbounded_graver_basis_path(self) -> None:
        code_text = notebook_code(JL_NOTEBOOK)

        self.assertIn("function compute_graver_basis_local(A)", code_text)
        self.assertIn("function graver_basis(A)", code_text)
        self.assertIn("G = graver_basis(A)", code_text)
        self.assertNotIn('write_mat("$(proj_path).lb"', code_text)
        self.assertNotIn('write_mat("$(proj_path).ub"', code_text)

    def test_python_notebook_avoids_deprecated_bqm_constructor(self) -> None:
        code_text = notebook_code(PY_NOTEBOOK)

        self.assertIn('dimod.BinaryQuadraticModel(Q, "BINARY", offset=offset)', code_text)
        self.assertNotIn("from_numpy_matrix", code_text)

    def test_python_notebook_has_a_local_graver_fallback_path(self) -> None:
        code_text = notebook_code(PY_NOTEBOOK)

        self.assertIn("from Py4ti2int32 import graver as py4ti2_graver", code_text)
        self.assertIn("HAS_PY4TI2 = False", code_text)
        self.assertIn("def load_precomputed_graver_basis() -> np.ndarray:", code_text)
        self.assertIn("urlretrieve(", code_text)
        self.assertIn("Py4ti2int32 is not available locally; loading the bundled graver.npy instead.", code_text)

    def test_notebooks_document_core_helpers(self) -> None:
        py_code = notebook_code(PY_NOTEBOOK)
        jl_code = notebook_code(JL_NOTEBOOK)

        for snippet in [
            '"""Return the index and value of the best augmentation candidate."""',
            '"""Compute the best integer step along a Graver direction within the box bounds."""',
            '"""Apply one of the notebook\'s Graver augmentation strategies until convergence."""',
        ]:
            self.assertIn(snippet, py_code)

        for snippet in [
            'Return the Graver basis of `A` by calling the bundled 4ti2 `graver` executable.',
            'Compute the best integer step size along a Graver direction within the box bounds.',
            'Plot the initial and augmented objectives together with the iteration counts.',
        ]:
            self.assertIn(snippet, jl_code)

    def test_notebooks_explain_the_qubo_sampling_strategy(self) -> None:
        py_markdown = notebook_markdown(PY_NOTEBOOK)
        jl_markdown = notebook_markdown(JL_NOTEBOOK)

        for markdown in [py_markdown, jl_markdown]:
            self.assertIn("x^\\top A^\\top A x - 2 b^\\top A x + b^\\top b", markdown)
            self.assertIn("diverse set of feasible starts", markdown)

    def test_julia_notebook_uses_npyread_for_the_graver_fallback(self) -> None:
        code_text = notebook_code(JL_NOTEBOOK)

        self.assertIn("NPZ.npyread(npy_path)", code_text)
        self.assertNotIn("NPZ.npzread", code_text)

    def test_julia_plot_helpers_capture_the_reviewed_experiment_labels(self) -> None:
        code_text = notebook_code(JL_NOTEBOOK)

        self.assertIn('function plot_augmentation(Y_feas, Y_aug, I_aug; experiment_name = "Augmentation")', code_text)
        self.assertIn('plot_augmentation(Y_feas, Y_aug, I_aug; experiment_name = "Full-basis augmentation")', code_text)
        self.assertIn('plot_augmentation(Y_feas, Y_paug, I_paug; experiment_name = "Partial-basis augmentation")', code_text)
        self.assertIn('function plot_multiple_partial_augmentation(Y_feas, Y_mpaug, global_minimum)', code_text)
        self.assertIn('ylabel     = "Objective gap to best full-basis result"', code_text)
        self.assertIn("yscale     = :log10", code_text)

    def test_julia_metadata_matches_the_committed_manifest(self) -> None:
        notebook = load_notebook(JL_NOTEBOOK)
        metadata_version = notebook["metadata"]["language_info"]["version"]
        self.assertEqual(metadata_version, manifest_julia_version(JL_MANIFEST))


if __name__ == "__main__":
    unittest.main()
