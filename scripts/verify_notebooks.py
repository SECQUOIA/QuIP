#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_NOTEBOOKS = (
    Path("notebooks_py/1-MathProg_python.ipynb"),
    Path("notebooks_jl/1-MathProg.ipynb"),
)
DEFAULT_JULIA_VERSION = "1.11"
FIND_JULIA_SCRIPT = REPO_ROOT / "scripts" / "find_julia.sh"
JULIA_KERNEL_PROJECT = REPO_ROOT / "scripts"
JULIA_KERNEL_NAME = "quip-julia-local"


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

    env = os.environ.copy()
    env.setdefault("JULIA_VERSION", DEFAULT_JULIA_VERSION)

    try:
        result = subprocess.run(
            [str(FIND_JULIA_SCRIPT)],
            cwd=REPO_ROOT,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        message = exc.stderr.strip() or exc.stdout.strip() or "Could not resolve a Julia executable."
        raise RuntimeError(message) from exc

    return result.stdout.strip()


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


def instantiate_julia_project(notebook: Path) -> None:
    run(
        [
            find_julia_executable(),
            "--project=./scripts",
            "-e",
            'include("./scripts/notebook_bootstrap.jl"); using .QuIPNotebookBootstrap; QuIPNotebookBootstrap.instantiate_notebook_project(ARGS[1]; precompile=true)',
            str(notebook),
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
            "JULIA_PKG_PRECOMPILE_AUTO": "0",
            "QUIP_NOTEBOOK_WARM_PACKAGES": "1",
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
        run(
            [
                find_julia_executable(),
                "--project=./scripts",
                "-e",
                "import Pkg; Pkg.instantiate()",
            ],
            env={
                "JULIA_DEPOT_PATH": default_julia_depot_path(),
                "JULIA_PKG_PRECOMPILE_AUTO": "0",
            },
        )
        with tempfile.TemporaryDirectory(prefix="quip-jupyter-kernels-") as tmp:
            kernel_name, env = julia_kernel_spec_dir(Path(tmp))
            for notebook in julia_notebooks:
                instantiate_julia_project(notebook)
                execute_notebook(notebook, kernel_name=kernel_name, env=env)

    print(f"Executed {len(notebooks)} notebook(s). Outputs written to {output_dir()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
