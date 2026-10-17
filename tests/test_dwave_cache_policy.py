from __future__ import annotations

import importlib.util
import os
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("dwave_cache_safety", ROOT / "scripts/verify_dwave_cache_safety.py")
safety = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(safety)


class DWaveCachePolicyTests(unittest.TestCase):
    def test_python_setup_overrides_an_existing_cache_directory(self):
        with patch.dict(os.environ, {"DWAVE_CACHE_HOME": "/untrusted-cache"}):
            exec(compile(safety.python_cache_setup(), "notebook cache setup", "exec"), {})
            self.assertEqual(os.environ["DWAVE_CACHE_HOME"], "off")

    def test_every_python_qpu_constructor_disables_persistent_cache(self):
        for options in safety.python_sampler_options():
            self.assertEqual(options.get("cache_home"), "off")


if __name__ == "__main__":
    unittest.main()
