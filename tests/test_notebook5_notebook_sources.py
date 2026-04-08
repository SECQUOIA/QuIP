from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_PY_PATH = REPO_ROOT / "notebooks_py" / "5-Benchmarking_python.ipynb"
NOTEBOOK_JL_PATH = REPO_ROOT / "notebooks_jl" / "5-Benchmarking.ipynb"
JULIA_DWAVE_ENVS = ("2-QUBO", "3-GAMA", "4-DWave", "5-Benchmarking", "sysimage")
DWAVE_MIN_VERSION = (0, 6, 3)


def load_notebook(path: Path) -> dict[str, object]:
    return json.loads(path.read_text())


def matching_code_cells(path: Path, needle: str) -> list[str]:
    notebook = load_notebook(path)
    cells: list[str] = []
    for cell in notebook["cells"]:
        source = "".join(cell.get("source", []))
        if cell.get("cell_type") == "code" and needle in source:
            cells.append(source)
    return cells


def matching_markdown_cells(path: Path, needle: str) -> list[str]:
    notebook = load_notebook(path)
    cells: list[str] = []
    for cell in notebook["cells"]:
        source = "".join(cell.get("source", []))
        if cell.get("cell_type") == "markdown" and needle in source:
            cells.append(source)
    return cells


def matching_profile_cells(path: Path, title_needle: str) -> list[str]:
    return [
        source
        for source in matching_code_cells(path, title_needle)
        if "Total number of reads (equivalent to time)" in source
    ]


def first_cell_with(path: Path, needle: str) -> str:
    for source in matching_code_cells(path, needle):
        return source
    raise AssertionError(f"Did not find {needle!r} in {path}.")


def extract_block(source: str, start: str, end: str) -> str:
    begin = source.index(start)
    finish = source.index(end, begin) if end in source[begin + len(start):] else len(source)
    return source[begin:finish]


class Notebook5SourceRegressionTests(unittest.TestCase):
    def test_instance_42_profile_cells_use_shared_builder_in_both_notebooks(self) -> None:
        title = "Performance Ratio of Ising 42 N=100"

        python_cells = matching_profile_cells(NOTEBOOK_PY_PATH, title)
        self.assertTrue(python_cells)
        for source in python_cells:
            self.assertIn("build_performance_ratio_profile(", source)
            self.assertIn("ax.set(ylim=[0.95, 1.001])", source)

        julia_cells = matching_profile_cells(NOTEBOOK_JL_PATH, title)
        self.assertTrue(julia_cells)
        for source in julia_cells:
            self.assertIn("build_performance_ratio_profile(", source)
            self.assertIn("ylims = (0.95, 1.001)", source)
            self.assertNotIn("rand(1:length(all_energies), boot_size)", source)
            self.assertNotIn("for _ in 1:n_boot_plot", source)

    def test_performance_ratio_labels_keep_formula_definition(self) -> None:
        python_source = first_cell_with(NOTEBOOK_PY_PATH, "performance_ratio_label =")
        self.assertIn(r"\mathrm{PR}=", python_source)
        self.assertIn(r"E_{\mathrm{rand}}", python_source)
        self.assertIn(r"E_{\min}", python_source)

        julia_source = first_cell_with(NOTEBOOK_JL_PATH, "performance_ratio_label =")
        self.assertIn(r"\mathrm{PR}=", julia_source)
        self.assertIn(r"E_{\mathrm{rand}}", julia_source)
        self.assertIn(r"E_{\min}", julia_source)

    def test_bootstrap_seed_tags_are_shared_between_notebooks(self) -> None:
        expected_tags = {
            "SEED_TAG_RESULTS_42": 44,
            "SEED_TAG_INSTANCE_42_PROFILE": 52,
            "SEED_TAG_ALL_RESULTS": 54,
            "SEED_TAG_ENSEMBLE_TTS": 57,
            "SEED_TAG_ENSEMBLE_PR_SWEEPS": 58,
            "SEED_TAG_ENSEMBLE_PR_READS": 59,
            "SEED_TAG_INSTANCE_42_TRANSFER_PROFILE": 62,
            "SEED_TAG_ENSEMBLE_TRANSFER_PROFILE": 65,
        }

        python_source = first_cell_with(NOTEBOOK_PY_PATH, "SEED_TAG_RESULTS_42 =")
        julia_source = first_cell_with(NOTEBOOK_JL_PATH, "SEED_TAG_RESULTS_42 =")

        for name, value in expected_tags.items():
            self.assertIn(f"{name} = {value}", python_source)
            self.assertIn(f"{name} = {value}", julia_source)

    def test_random_instance_generator_is_shared_between_notebooks(self) -> None:
        python_source = first_cell_with(NOTEBOOK_PY_PATH, "def build_random_ising_instance")
        python_block = extract_block(
            python_source,
            "def deterministic_uniform_values",
            "def load_or_generate_sa_samples",
        )
        self.assertIn("deterministic_uniform_values", python_block)
        self.assertNotIn("np.random.RandomState", python_block)

        julia_source = first_cell_with(NOTEBOOK_JL_PATH, "function build_random_ising_instance")
        julia_block = extract_block(
            julia_source,
            "function deterministic_uniform_values",
            "function load_or_generate_solution",
        )
        self.assertIn("deterministic_uniform_values", julia_block)
        self.assertNotIn("MersenneTwister", julia_block)
        self.assertIn("permutedims(reshape(J_values, n, n))", julia_block)

    def test_example2_instance_setup_is_shared_between_notebooks(self) -> None:
        python_source = first_cell_with(NOTEBOOK_PY_PATH, "EXAMPLE2_SEED =")
        self.assertIn("EXAMPLE2_SEED = 42", python_source)
        self.assertIn("example2_uniform_values", python_source)
        self.assertNotIn("np.random.seed", python_source)

        julia_source = first_cell_with(NOTEBOOK_JL_PATH, "const EXAMPLE2_SEED =")
        self.assertIn("const EXAMPLE2_SEED = 42", julia_source)
        self.assertIn("example2_uniform_values", julia_source)
        self.assertNotIn("Random.seed!", julia_source)
        self.assertIn("permutedims(reshape(example2_uniform_values", julia_source)

    def test_julia_profile_cache_path_uses_dwavel_neal_optimizer(self) -> None:
        julia_source = first_cell_with(NOTEBOOK_JL_PATH, "function load_or_generate_solution")
        self.assertIn("neal_sample_ising", julia_source)
        self.assertIn('set_optimizer(instance_model, DWave.Neal.Optimizer)', julia_source)
        self.assertIn("QUBOTools.solution(unsafe_backend(instance_model))", julia_source)
        self.assertNotIn('pyimport("dwave.samplers")', julia_source)
        self.assertNotIn("direct_sample_ising", julia_source)
        self.assertNotIn("MODEL_ISING_DATA", julia_source)

    def test_julia_notebook_documents_dwavel_directly(self) -> None:
        markdown_cells = matching_markdown_cells(NOTEBOOK_JL_PATH, "DWave.jl")
        self.assertTrue(markdown_cells)

        joined_markdown = "\n".join(markdown_cells)
        self.assertNotIn("dwave.samplers", joined_markdown)
        self.assertNotIn("PythonCall", joined_markdown)
        self.assertNotIn("JuliaQUBO/DWave.jl/issues/15", joined_markdown)

    def test_all_julia_envs_use_released_dwavel(self) -> None:
        for env in JULIA_DWAVE_ENVS:
            manifest_path = REPO_ROOT / "notebooks_jl" / "envs" / env / "Manifest.toml"
            manifest = manifest_path.read_text()

            match = re.search(
                r'\[\[deps\.DWave\]\].*?version = "(\d+)\.(\d+)\.(\d+)"',
                manifest,
                re.S,
            )
            self.assertIsNotNone(match, f"DWave entry not found in {env}/Manifest.toml")
            version = tuple(int(match.group(i)) for i in (1, 2, 3))
            self.assertGreaterEqual(
                version,
                DWAVE_MIN_VERSION,
                f"{env}: DWave {'.'.join(map(str, version))} < {'.'.join(map(str, DWAVE_MIN_VERSION))}",
            )
            self.assertNotIn(
                "repo-rev",
                manifest.split("[[deps.DWave]]")[1].split("[[")[0],
                f"{env}: DWave should come from the registry, not a git pin",
            )


if __name__ == "__main__":
    unittest.main()
