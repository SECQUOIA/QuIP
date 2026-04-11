from __future__ import annotations

import importlib.util
import os
import re
import unittest
from pathlib import Path
from unittest.mock import patch


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "verify_notebooks.py"
SPEC = importlib.util.spec_from_file_location("verify_notebooks", MODULE_PATH)
assert SPEC is not None
assert SPEC.loader is not None
verify_notebooks = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verify_notebooks)
MAKEFILE_PATH = Path(__file__).resolve().parents[1] / "Makefile"
WORKFLOW_PATH = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "jupyter-book.yml"
LOCAL_SETUP_PATH = Path(__file__).resolve().parents[1] / "local-setup.md"
VERIFY_JULIA_SMOKES_PATH = Path(__file__).resolve().parents[1] / "scripts" / "verify_julia_env_smokes.jl"
VERIFY_NOTEBOOK5_JULIA_CACHE_SMOKE_PATH = (
    Path(__file__).resolve().parents[1] / "scripts" / "verify_notebook5_julia_cache_smoke.jl"
)


class ParseExecutionTimeoutSecondsTests(unittest.TestCase):
    def test_uses_default_timeout_when_env_is_unset(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(verify_notebooks.parse_execution_timeout_seconds(), 1200)

    def test_accepts_valid_integer_timeout(self) -> None:
        with patch.dict(os.environ, {"QUIP_NOTEBOOK_TIMEOUT": "3600"}, clear=True):
            self.assertEqual(verify_notebooks.parse_execution_timeout_seconds(), 3600)

    def test_rejects_non_integer_timeout_with_clear_message(self) -> None:
        with patch.dict(os.environ, {"QUIP_NOTEBOOK_TIMEOUT": "fast"}, clear=True):
            with self.assertRaisesRegex(
                ValueError,
                r"Invalid QUIP_NOTEBOOK_TIMEOUT value 'fast': must be an integer number of seconds\.",
            ):
                verify_notebooks.parse_execution_timeout_seconds()

    def test_rejects_non_positive_timeout_with_clear_message(self) -> None:
        with patch.dict(os.environ, {"QUIP_NOTEBOOK_TIMEOUT": "0"}, clear=True):
            with self.assertRaisesRegex(
                ValueError,
                r"Invalid QUIP_NOTEBOOK_TIMEOUT value '0': must be a positive integer number of seconds\.",
            ):
                verify_notebooks.parse_execution_timeout_seconds()


class InstantiateJuliaKernelProjectTests(unittest.TestCase):
    @patch.object(verify_notebooks, "run")
    def test_instantiates_scripts_project_with_repo_depot(
        self,
        run_mock: unittest.mock.Mock,
    ) -> None:
        with patch.dict(os.environ, {}, clear=True):
            verify_notebooks.instantiate_julia_kernel_project(julia_executable="/tmp/julia")

        run_mock.assert_called_once()
        cmd = run_mock.call_args.args[0]
        env = run_mock.call_args.kwargs["env"]

        self.assertEqual(cmd[0], "/tmp/julia")
        self.assertEqual(cmd[1], "--project=./scripts")
        self.assertIn("QuIPNotebookBootstrap.instantiate_scripts_project", cmd[3])
        self.assertIn(str(Path.home() / ".julia"), env["JULIA_DEPOT_PATH"])
        self.assertEqual(env["JULIA_PKG_PRECOMPILE_AUTO"], "0")


class NotebookJuliaVersionTests(unittest.TestCase):
    def test_reads_julia_patch_version_from_notebook_manifest(self) -> None:
        self.assertEqual(
            verify_notebooks.notebook_manifest_julia_version(Path("notebooks_jl/1-MathProg.ipynb")),
            "1.11.5",
        )
        self.assertEqual(
            verify_notebooks.notebook_manifest_julia_version(Path("notebooks_jl/5-Benchmarking.ipynb")),
            "1.11.9",
        )

    @patch("subprocess.run")
    def test_find_julia_executable_accepts_notebook_specific_version(
        self,
        run_mock: unittest.mock.Mock,
    ) -> None:
        run_mock.return_value = unittest.mock.Mock(stdout="/tmp/julia\n")
        path = verify_notebooks.find_julia_executable("1.11.9")

        self.assertEqual(path, "/tmp/julia")
        self.assertEqual(run_mock.call_args.kwargs["env"]["JULIA_VERSION"], "1.11.9")


class SetupJuliaTargetTests(unittest.TestCase):
    def test_setup_julia_instantiates_scripts_project_before_notebook_project(self) -> None:
        makefile = MAKEFILE_PATH.read_text()
        match = re.search(r"^setup-julia:\n(?P<body>(?:\t.*\n)+)", makefile, re.MULTILINE)
        assert match is not None
        body = match.group("body")

        self.assertIn("QuIPNotebookBootstrap.instantiate_scripts_project", body)
        self.assertIn("QuIPNotebookBootstrap.instantiate_notebook_project", body)
        self.assertLess(
            body.index("QuIPNotebookBootstrap.instantiate_scripts_project"),
            body.index("QuIPNotebookBootstrap.instantiate_notebook_project"),
        )

    def test_notebook5_cache_smoke_target_runs_dedicated_script(self) -> None:
        makefile = MAKEFILE_PATH.read_text()
        match = re.search(
            r"^verify-julia-notebook5-cache-smoke:\n(?P<body>(?:\t.*\n)+)",
            makefile,
            re.MULTILINE,
        )
        assert match is not None
        body = match.group("body")

        self.assertIn("./scripts/verify_notebook5_julia_cache_smoke.jl", body)


class JuliaSmokeScriptTests(unittest.TestCase):
    def test_smoke_script_loads_ijulia_via_core_eval_after_scripts_project(self) -> None:
        source = VERIFY_JULIA_SMOKES_PATH.read_text()

        self.assertIn("QuIPNotebookBootstrap.instantiate_scripts_project", source)
        self.assertIn("Core.eval(Main, :(import IJulia))", source)
        self.assertNotIn("\n    import IJulia\n", source)
        self.assertLess(
            source.index("QuIPNotebookBootstrap.instantiate_scripts_project"),
            source.index("Core.eval(Main, :(import IJulia))"),
        )


class WorkflowCoverageTests(unittest.TestCase):
    def test_workflow_runs_julia_notebook_smokes(self) -> None:
        workflow = WORKFLOW_PATH.read_text()

        self.assertIn("julia-notebook-smokes:", workflow)
        self.assertIn("make verify-julia-colab-smokes COLAB_JULIA_SMOKE_NOTEBOOKS=5-Benchmarking", workflow)
        self.assertIn("make verify-julia-notebook5-cache-smoke", workflow)


class Notebook5CacheSmokeTests(unittest.TestCase):
    def test_cache_smoke_loads_helpers_from_notebook_source(self) -> None:
        source = VERIFY_NOTEBOOK5_JULIA_CACHE_SMOKE_PATH.read_text()

        self.assertIn("NOTEBOOK_5_BENCHMARK_HELPERS_END", source)
        self.assertIn("Base.include_string", source)
        self.assertIn("build_random_ising_instance", source)
        self.assertNotIn("\nfunction neal_sample_ising(", source)
        self.assertNotIn("\nfunction load_or_generate_solution(", source)


class JuliaVersionSelectionTests(unittest.TestCase):
    def test_make_targets_do_not_force_a_single_julia_binary_for_notebook_execution(self) -> None:
        makefile = MAKEFILE_PATH.read_text()
        verify_notebooks_target = re.search(
            r"^verify-notebooks:\n(?P<body>(?:\t.*\n)+)",
            makefile,
            re.MULTILINE,
        )
        verify_julia_colab_notebooks_target = re.search(
            r"^verify-julia-colab-notebooks:\n(?P<body>(?:\t.*\n)+)",
            makefile,
            re.MULTILINE,
        )
        assert verify_notebooks_target is not None
        assert verify_julia_colab_notebooks_target is not None

        self.assertNotIn("JULIA_BIN=", verify_notebooks_target.group("body"))
        self.assertNotIn("JULIA_BIN=", verify_julia_colab_notebooks_target.group("body"))

    def test_benchmarking_smoke_defaults_match_benchmarking_manifest(self) -> None:
        benchmarking_version = verify_notebooks.notebook_manifest_julia_version(
            Path("notebooks_jl/5-Benchmarking.ipynb")
        )
        workflow = WORKFLOW_PATH.read_text()
        makefile = MAKEFILE_PATH.read_text()

        assert benchmarking_version is not None
        self.assertIn(f"COLAB_JULIA_VERSION ?= {benchmarking_version}", makefile)
        self.assertIn(f'version: "{benchmarking_version}"', workflow)

    def test_local_setup_documents_the_mixed_julia_patch_versions(self) -> None:
        local_setup = LOCAL_SETUP_PATH.read_text()

        self.assertIn("juliaup add 1.11.5", local_setup)
        self.assertIn("juliaup add 1.11.9", local_setup)
        self.assertIn("COLAB_JULIA_VERSION=1.11.9", local_setup)
        self.assertIn(".julia-colab-depot", local_setup)


if __name__ == "__main__":
    unittest.main()
