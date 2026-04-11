from __future__ import annotations

import json
import math
import os
import pickle
import unittest
from pathlib import Path

import numpy as np


NOTEBOOK_PATH = Path(__file__).resolve().parents[1] / "notebooks_py" / "5-Benchmarking_python.ipynb"
MARKER_START = "# NOTEBOOK_5_BENCHMARK_HELPERS_START"
MARKER_END = "# NOTEBOOK_5_BENCHMARK_HELPERS_END"


def load_helper_namespace() -> dict[str, object]:
    notebook = json.loads(NOTEBOOK_PATH.read_text())
    for cell in notebook["cells"]:
        source = "".join(cell.get("source", []))
        if MARKER_START in source and MARKER_END in source:
            helper_source = source.split(MARKER_START, 1)[1].split(MARKER_END, 1)[0]
            namespace: dict[str, object] = {
                "np": np,
                "math": math,
                "os": os,
                "pickle": pickle,
            }
            exec(helper_source, namespace)
            return namespace
    raise AssertionError("Notebook 5 helper block markers were not found.")


class Notebook5BootstrapHelperTests(unittest.TestCase):
    def setUp(self) -> None:
        self.helpers = load_helper_namespace()

    def test_reference_bootstrap_indices_are_deterministic(self) -> None:
        bootstrap_indices = self.helpers["bootstrap_indices"]
        idx1 = bootstrap_indices(5, 3, 4, 11, 7)
        idx2 = bootstrap_indices(5, 3, 4, 11, 7)
        np.testing.assert_array_equal(idx1, idx2)
        self.assertEqual(idx1.shape, (4, 3))

    def test_seeded_random_bootstrap_path_is_repeatable(self) -> None:
        bootstrap_indices = self.helpers["bootstrap_indices"]
        self.helpers["use_reference_bootstrap"] = False
        self.helpers["bootstrap_rng_seed"] = 123

        idx1 = bootstrap_indices(7, 4, 5, 9, 1)
        idx2 = bootstrap_indices(7, 4, 5, 9, 1)

        np.testing.assert_array_equal(idx1, idx2)
        self.assertTrue(np.all((0 <= idx1) & (idx1 < 7)))

    def test_performance_ratio_profile_returns_ordered_confidence_bounds(self) -> None:
        build_profile = self.helpers["build_performance_ratio_profile"]
        energies = np.asarray([-7.0, -6.5, -6.0, -5.0, -4.0, -3.5], dtype=float)

        ratios, intervals = build_profile(
            energies,
            [1, 2, 4],
            n_boot=64,
            random_energy=-2.0,
            min_energy=-7.0,
            ci=68,
            seed_parts=(42, 62, 10),
        )

        self.assertEqual(ratios.shape, (3,))
        self.assertEqual(intervals.shape, (3, 2))
        self.assertTrue(np.all(intervals[:, 0] <= ratios))
        self.assertTrue(np.all(ratios <= intervals[:, 1]))

        ratios_repeat, intervals_repeat = build_profile(
            energies,
            [1, 2, 4],
            n_boot=64,
            random_energy=-2.0,
            min_energy=-7.0,
            ci=68,
            seed_parts=(42, 62, 10),
        )
        np.testing.assert_allclose(ratios, ratios_repeat)
        np.testing.assert_allclose(intervals, intervals_repeat)


if __name__ == "__main__":
    unittest.main()
