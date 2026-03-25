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
    @patch.object(verify_notebooks, "find_julia_executable", return_value="/tmp/julia")
    def test_instantiates_scripts_project_with_repo_depot(
        self,
        _find_julia_executable: unittest.mock.Mock,
        run_mock: unittest.mock.Mock,
    ) -> None:
        with patch.dict(os.environ, {}, clear=True):
            verify_notebooks.instantiate_julia_kernel_project()

        run_mock.assert_called_once()
        cmd = run_mock.call_args.args[0]
        env = run_mock.call_args.kwargs["env"]

        self.assertEqual(cmd[0], "/tmp/julia")
        self.assertEqual(cmd[1], "--project=./scripts")
        self.assertIn("QuIPNotebookBootstrap.instantiate_scripts_project", cmd[3])
        self.assertIn(str(Path.home() / ".julia"), env["JULIA_DEPOT_PATH"])
        self.assertEqual(env["JULIA_PKG_PRECOMPILE_AUTO"], "0")


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


if __name__ == "__main__":
    unittest.main()
