#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_NOTEBOOKS = (
    Path("notebooks_py/1-MathProg_python.ipynb"),
    Path("notebooks_jl/1-MathProg.ipynb"),
)
JULIA_PROJECT = REPO_ROOT / "notebooks_jl"
JULIA_KERNEL_PROJECT = REPO_ROOT / "scripts"
JULIA_KERNEL_NAME = "quip-julia-local"
JULIAUP_VERSION = re.compile(r"julia-(\d+)\.(\d+)\.(\d+)")


def default_julia_depot_path() -> str:
    configured = os.environ.get("JULIA_DEPOT_PATH")
    if configured:
        return configured
    depots = [str(REPO_ROOT / ".julia-depot"), str(Path.home() / ".julia")]
    return os.pathsep.join(depots)


def find_julia_executable() -> str:
    configured = os.environ.get("JULIA_BIN")
    if configured:
        return configured
    candidate = shutil.which("julia")
    if candidate is None:
        raise RuntimeError("Could not find `julia` on PATH.")
    resolved = Path(candidate).resolve()
    if resolved.name == "julialauncher":
        juliaup_root = Path.home() / ".julia" / "juliaup"
        binaries = sorted(juliaup_root.glob("*/bin/julia"), key=juliaup_binary_key)
        if binaries:
            return str(binaries[-1])
    return candidate


def juliaup_binary_key(path: Path) -> tuple[int, int, int, str]:
    match = JULIAUP_VERSION.search(path.as_posix())
    if match:
        return tuple(int(part) for part in match.groups()) + (path.as_posix(),)
    return (0, 0, 0, path.as_posix())


def merged_env(overrides: dict[str, str] | None = None) -> dict[str, str]:
    env = os.environ.copy()
    if overrides:
        env.update(overrides)
    return env


def run(cmd: list[str], *, env: dict[str, str] | None = None) -> None:
    print("+", " ".join(cmd))
    subprocess.run(cmd, cwd=REPO_ROOT, env=merged_env(env), check=True)


def output_dir() -> Path:
    path = REPO_ROOT / ".nbverify"
    path.mkdir(exist_ok=True)
    return path


def classify_notebook(path: Path) -> str:
    if "notebooks_py" in path.parts:
        return "python"
    if "notebooks_jl" in path.parts:
        return "julia"
    raise ValueError(f"Unsupported notebook path: {path}")


def instantiate_julia_project() -> None:
    run(
        [
            find_julia_executable(),
            "--project=./notebooks_jl",
            "-e",
            "import Pkg; Pkg.resolve(); Pkg.instantiate()",
        ],
        env={
            "JULIA_DEPOT_PATH": default_julia_depot_path(),
            "JULIA_PKG_PRECOMPILE_AUTO": "0",
        },
    )


def julia_kernel_spec_dir(tmpdir: Path) -> tuple[str, dict[str, str]]:
    julia_exe = find_julia_executable()
    kernels_dir = tmpdir / "kernels" / JULIA_KERNEL_NAME
    kernels_dir.mkdir(parents=True, exist_ok=True)
    kernel_spec = {
        "argv": [
            julia_exe,
            "-i",
            "--color=yes",
            f"--project={JULIA_KERNEL_PROJECT}",
            "-e",
            "import IJulia; IJulia.run_kernel()",
            "{connection_file}",
        ],
        "display_name": "QuIP Julia (local)",
        "language": "julia",
        "env": {
            "JULIA_DEPOT_PATH": default_julia_depot_path(),
            "JULIA_LOAD_PATH": f"{JULIA_PROJECT}:{JULIA_KERNEL_PROJECT}:@stdlib",
        },
        "interrupt_mode": "signal",
    }
    (kernels_dir / "kernel.json").write_text(json.dumps(kernel_spec, indent=2) + "\n")
    env = {
        "JUPYTER_PATH": str(tmpdir),
        "JULIA_DEPOT_PATH": default_julia_depot_path(),
        "JULIA_PKG_PRECOMPILE_AUTO": "0",
    }
    return JULIA_KERNEL_NAME, env


def execute_notebook(path: Path, *, kernel_name: str | None = None, env: dict[str, str] | None = None) -> None:
    outdir = output_dir()
    cmd = [
        sys.executable,
        "-m",
        "jupyter",
        "nbconvert",
        "--to",
        "notebook",
        "--execute",
        "--ExecutePreprocessor.timeout=1200",
        "--output-dir",
        str(outdir),
    ]
    if kernel_name is not None:
        cmd.append(f"--ExecutePreprocessor.kernel_name={kernel_name}")
    cmd.append(str(path))
    run(cmd, env=env)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Execute selected QuIP notebooks locally through Jupyter."
    )
    parser.add_argument(
        "notebooks",
        nargs="*",
        default=[str(path) for path in DEFAULT_NOTEBOOKS],
        help="Notebook paths relative to the repository root.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    notebooks = [Path(path) for path in args.notebooks]

    for notebook in notebooks:
        if not (REPO_ROOT / notebook).is_file():
            raise FileNotFoundError(f"Notebook not found: {notebook}")

    julia_notebooks = [path for path in notebooks if classify_notebook(path) == "julia"]
    python_notebooks = [path for path in notebooks if classify_notebook(path) == "python"]

    for notebook in python_notebooks:
        execute_notebook(notebook, kernel_name="python3")

    if julia_notebooks:
        instantiate_julia_project()
        run(
            [
                find_julia_executable(),
                "--project=./scripts",
                "-e",
                "import Pkg; Pkg.resolve(); Pkg.instantiate()",
            ],
            env={
                "JULIA_DEPOT_PATH": default_julia_depot_path(),
                "JULIA_PKG_PRECOMPILE_AUTO": "0",
            },
        )
        with tempfile.TemporaryDirectory(prefix="quip-jupyter-kernels-") as tmp:
            kernel_name, env = julia_kernel_spec_dir(Path(tmp))
            for notebook in julia_notebooks:
                execute_notebook(notebook, kernel_name=kernel_name, env=env)

    print(f"Executed {len(notebooks)} notebook(s). Outputs written to {output_dir()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
