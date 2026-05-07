from __future__ import annotations

import json
import numpy as np
import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PY_NOTEBOOK = REPO_ROOT / "notebooks_py" / "3-GAMA_python.ipynb"
JL_NOTEBOOK = REPO_ROOT / "notebooks_jl" / "3-GAMA.ipynb"
JL_MANIFEST = REPO_ROOT / "notebooks_jl" / "envs" / "3-GAMA" / "Manifest.toml"
NOTEBOOK_DATA_DIR = REPO_ROOT / "notebooks_data"
COEFF_FILE = NOTEBOOK_DATA_DIR / "3-GAMA_example4_coefficients.csv"
FEASIBLE_STARTS_FILE = NOTEBOOK_DATA_DIR / "3-GAMA_example4_feasible_starts.csv"
GRAVER_ORDER_FILE = NOTEBOOK_DATA_DIR / "3-GAMA_example4_graver_order.csv"


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


def notebook_stderr(path: Path) -> str:
    notebook = load_notebook(path)
    chunks: list[str] = []
    for cell in notebook["cells"]:
        for output in cell.get("outputs", []):
            if output.get("output_type") == "stream" and output.get("name") == "stderr":
                text = output.get("text", [])
                chunks.append("".join(text) if isinstance(text, list) else str(text))
    return "\n".join(chunks)


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
                "### Class examples",
                "### Example 4: saved portfolio instance",
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
                "### Class examples",
                "### Example 4: saved portfolio instance",
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

    def test_both_notebooks_link_intro_references_to_the_reference_section(self) -> None:
        for path, prefix in [(PY_NOTEBOOK, "gama-python"), (JL_NOTEBOOK, "gama-julia")]:
            markdown = notebook_markdown(path)
            self.assertIn(f"[Reference [1]](#{prefix}-reference-1)", markdown)
            self.assertIn(f"[Reference [2]](#{prefix}-reference-2)", markdown)
            self.assertIn(f"({prefix}-reference-1)=\n- [1]", markdown)
            self.assertIn(f"({prefix}-reference-2)=\n- [2]", markdown)
            self.assertIn(f"({prefix}-reference-3)=\n- [3]", markdown)
            self.assertNotIn('<a id="reference-1"></a>', markdown)
            self.assertNotIn('<a id="reference-2"></a>', markdown)
            self.assertNotIn('<a id="reference-3"></a>', markdown)

    def test_both_notebooks_share_the_same_core_narrative_anchors(self) -> None:
        py_markdown = notebook_markdown(PY_NOTEBOOK)
        jl_markdown = notebook_markdown(JL_NOTEBOOK)

        for anchor in [
            "The original GAMA class notebook used `EXAMPLE = 1`, `EXAMPLE = 2`, `EXAMPLE = 3`, and `EXAMPLE = 4`.",
            "#### Example 1: illustrative Graver augmentation",
            "#### Example 2: four-variable linear example",
            "#### Example 3: alternate four-variable linear example",
            "The remaining GAMA method below uses this saved Example 4 instance",
            "First we would write this problem as an unconstrained one by penalizing the linear constraints as quadratics in the objective.",
            "Now we can highlight another feature of the algorithm, computing starting feasible solutions.",
            "We use simulated annealing here because the goal is not a single feasible point but a diverse set of feasible starts.",
            "The Graver basis of this matrix $A$ has 29789 elements",
        ]:
            self.assertIn(anchor, py_markdown)
            self.assertIn(anchor, jl_markdown)

        for example_snippet in [
            r"A = \begin{bmatrix} 1 & 1 & 1 & 1 \\ 1 & 5 & 10 & 25 \end{bmatrix}",
            r"x^{(0)} = \begin{bmatrix} 1 & 15 & 3 & 2 \end{bmatrix}",
            r"c = \begin{bmatrix} 0 & 1 & 0 & 2 \end{bmatrix}",
            r"x^{(0)} = \begin{bmatrix} 1 & 8 & 0 & 1 \end{bmatrix}",
            r"c = \begin{bmatrix} 1 & 3 & 14 & 17 \end{bmatrix}",
            r"x^{(0)} = \begin{bmatrix} 3 & 0 & 6 & 1 \end{bmatrix}",
        ]:
            self.assertIn(example_snippet, py_markdown)
            self.assertIn(example_snippet, jl_markdown)

    def test_shared_example_data_files_have_expected_shapes(self) -> None:
        coeffs = np.loadtxt(COEFF_FILE, delimiter=",")
        feasible_starts = np.loadtxt(FEASIBLE_STARTS_FILE, delimiter=",", dtype=int)
        graver_order = np.loadtxt(GRAVER_ORDER_FILE, delimiter=",", dtype=int)

        self.assertEqual(coeffs.shape, (2, 25))
        self.assertEqual(feasible_starts.shape, (20, 25))
        self.assertEqual(graver_order.shape, (29789,))
        self.assertEqual(len(np.unique(graver_order)), 29789)

    def test_both_notebooks_use_shared_instance_data_by_default(self) -> None:
        py_code = notebook_code(PY_NOTEBOOK)
        jl_code = notebook_code(JL_NOTEBOOK)
        py_markdown = notebook_markdown(PY_NOTEBOOK)
        jl_markdown = notebook_markdown(JL_NOTEBOOK)

        for code_text in [py_code, jl_code]:
            self.assertIn("3-GAMA_example4_coefficients.csv", code_text)
            self.assertIn("3-GAMA_example4_feasible_starts.csv", code_text)
            self.assertIn("3-GAMA_example4_graver_order.csv", code_text)
            self.assertNotIn('"3-GAMA_coefficients.csv"', code_text)
            self.assertNotIn('"3-GAMA_feasible_starts.csv"', code_text)
            self.assertNotIn('"3-GAMA_graver_order.csv"', code_text)

        for markdown in [py_markdown, jl_markdown]:
            self.assertIn("saved Example 4 instance", markdown)
            self.assertIn("reproducible", markdown)
            self.assertNotIn("directly comparable", markdown)
            self.assertNotIn("both notebooks load", markdown)
            self.assertNotIn("Python and Julia versions begin", markdown)
            self.assertNotIn("Julia and Python versions begin", markdown)
            self.assertNotIn("notebooks_data/3-GAMA_coefficients.csv", markdown)
            self.assertNotIn("notebooks_data/3-GAMA_feasible_starts.csv", markdown)
            self.assertNotIn("notebooks_data/3-GAMA_graver_order.csv", markdown)

        self.assertLess(
            py_code.index("def load_precomputed_feasible_starts"),
            py_code.index("def get_feasible(A, b"),
        )
        self.assertLess(
            py_code.index("def load_graver_order"),
            py_code.index("def get_feasible(A, b"),
        )
        self.assertLess(
            jl_code.index("function load_precomputed_feasible_starts"),
            jl_code.index("function get_feasible(A, b"),
        )
        self.assertLess(
            jl_code.index("function load_graver_order"),
            jl_code.index("function get_feasible(A, b"),
        )

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
            "The number of iterations performed, the last objective value, and the final point.",
        ]:
            self.assertIn(snippet, py_code)

        for snippet in [
            'Return the Graver basis of `A` by calling the bundled 4ti2 `graver` executable.',
            'Compute the best integer step size along a Graver direction within the box bounds.',
            'The boxplot object with zero-gap entries lifted for the log axis.',
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

    def test_notebooks_use_the_same_objective_sign_convention(self) -> None:
        py_code = notebook_code(PY_NOTEBOOK)
        jl_code = notebook_code(JL_NOTEBOOK)

        self.assertIn("return -np.dot(mu, x)", py_code)
        self.assertIn("f(x) = -μ'x +", jl_code)
        self.assertNotIn("f(x) = μ'x +", jl_code)

    def test_julia_markdown_avoids_literal_backslash_n_sequences(self) -> None:
        self.assertNotIn("\\n", notebook_markdown(JL_NOTEBOOK))

    def test_python_plotting_cells_use_shared_labels_and_log_axes(self) -> None:
        code_text = notebook_code(PY_NOTEBOOK)
        markdown = notebook_markdown(PY_NOTEBOOK)

        self.assertIn("Complete-basis greedy ({len(r)} directions)", code_text)
        self.assertIn("Partial-basis greedy ({n_draws} directions)", code_text)
        self.assertNotIn("Complete-basis greedy augmentation\\n", code_text)
        self.assertNotIn("Partial-basis greedy augmentation\\n", code_text)
        self.assertIn("plot_objective_gap_boxplot", code_text)
        self.assertIn("Objective gap to best full-basis result", code_text)
        self.assertIn("sample_labels = [f'{10 * i}% |G|' for i in range(1, N)]", code_text)
        self.assertIn("sample_labels.append('Complete basis')", code_text)
        self.assertIn("f'{t:.1e}'", code_text)
        self.assertIn("ax1.set_yscale('log')", code_text)
        self.assertIn("This speed/quality tradeoff motivates the next experiment", markdown)
        self.assertNotIn("...the time to do augmentation only having 10 choices is minimal", markdown)

    def test_julia_plot_helpers_capture_the_reviewed_experiment_labels(self) -> None:
        code_text = notebook_code(JL_NOTEBOOK)
        markdown = notebook_markdown(JL_NOTEBOOK)

        self.assertIn('function plot_augmentation(Y_feas, Y_aug, I_aug; experiment_name = "Augmentation")', code_text)
        self.assertIn('top_margin = 6mm', code_text)
        self.assertIn('plot_augmentation(Y_feas, Y_aug, I_aug; experiment_name = "Complete-basis greedy ($(size(G, 1)) directions)")', code_text)
        self.assertIn('plot_augmentation(Y_feas, Y_paug, I_paug; experiment_name = "Partial-basis greedy ($(num_partial_directions) directions)")', code_text)
        self.assertNotIn('Complete-basis greedy augmentation\\n', code_text)
        self.assertNotIn('Partial-basis greedy augmentation\\n', code_text)
        self.assertIn('function plot_augmentation_runtime(T_aug, T_paug; partial_label = "10 sampled Graver directions")', code_text)
        self.assertIn('function log_ticks_for(values; include_zero_floor = nothing)', code_text)
        self.assertIn("legend     = :outertopright", code_text)
        self.assertIn("right_margin = 18mm", code_text)
        self.assertNotIn("legend     = (0.75, 0.25)", code_text)
        self.assertNotIn("legend     = :topright", code_text)
        self.assertIn('function plot_multiple_partial_augmentation(Y_feas, Y_mpaug, global_minimum)', code_text)
        self.assertIn('function lift_zero_gaps(Y, global_minimum)', code_text)
        self.assertIn('"$(10i)% |G|"', code_text)
        self.assertIn('@sprintf("%.1e", t)', code_text)
        self.assertNotIn('"\\$ $(10i) %|G| \\$"', code_text)
        self.assertNotIn('"\\$ $(10i) \\%|G| \\$"', code_text)
        self.assertIn('ylabel     = "Objective gap to best full-basis result"', code_text)
        self.assertIn('yticks     = (ticks, labels)', code_text)
        self.assertIn("yscale     = :log10", code_text)
        self.assertIn("This speed/quality tradeoff motivates the next experiment", markdown)
        self.assertNotIn("...the time to do augmentation only having 10 choices is minimal", markdown)

    def test_committed_julia_outputs_do_not_include_plot_label_errors(self) -> None:
        stderr = notebook_stderr(JL_NOTEBOOK)

        self.assertNotIn("ERROR: syntax error", stderr)
        self.assertNotIn("No strict ticks found", stderr)

    def test_julia_metadata_matches_the_committed_manifest(self) -> None:
        notebook = load_notebook(JL_NOTEBOOK)
        metadata_version = notebook["metadata"]["language_info"]["version"]
        self.assertEqual(metadata_version, manifest_julia_version(JL_MANIFEST))


if __name__ == "__main__":
    unittest.main()
