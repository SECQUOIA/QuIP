#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import shutil
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
FIND_JULIA_SCRIPT = REPO_ROOT / "scripts" / "find_julia.sh"
QCI_NOTEBOOK = REPO_ROOT / "notebooks_py" / "6-QCi_python.ipynb"
ALLOW_VERSION_MISMATCH_ENV = "QUIP_ALLOW_JULIA_VERSION_MISMATCH"
DEFAULT_JULIA_NOTEBOOK_PROJECTS = (
    "1-MathProg",
    "2-QUBO",
    "3-GAMA",
    "4-DWave",
    "5-Benchmarking",
)
DEFAULT_JULIA_INSTANTIATE_PROJECTS = (
    "1-MathProg",
    "2-QUBO",
    "3-GAMA",
    "4-DWave",
    "5-Benchmarking",
)


def format_cmd(cmd: list[str]) -> str:
    return " ".join(shlex.quote(str(part)) for part in cmd)


def run(
    cmd: list[str],
    *,
    cwd: Path = REPO_ROOT,
    env: dict[str, str] | None = None,
    capture_output: bool = False,
) -> subprocess.CompletedProcess[str]:
    print("+", format_cmd(cmd), flush=True)
    return subprocess.run(
        cmd,
        cwd=cwd,
        env=env,
        check=True,
        text=True,
        capture_output=capture_output,
    )


def venv_python(venv_dir: Path) -> Path:
    if os.name == "nt":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def notebook_code(path: Path) -> str:
    notebook = json.loads(path.read_text(encoding="utf-8"))
    return "\n".join(
        "".join(cell.get("source", []))
        for cell in notebook["cells"]
        if cell.get("cell_type") == "code"
    )


def run_python_ocean_smoke(python_executable: str) -> None:
    with tempfile.TemporaryDirectory(prefix="quip-colab-ocean-") as tmp:
        venv_dir = Path(tmp) / "venv"
        run([python_executable, "-m", "venv", str(venv_dir)])

        python = venv_python(venv_dir)
        run([str(python), "-m", "pip", "install", "-q", "--upgrade", "pip"])
        run([str(python), "-m", "pip", "install", "-q", "dwave-ocean-sdk"])
        run(
            [
                str(python),
                "-c",
                "\n".join(
                    [
                        "import dimod",
                        "from dwave.samplers import SimulatedAnnealingSampler",
                        "bqm = dimod.BinaryQuadraticModel.from_qubo({('x', 'x'): -1.0})",
                        "samples = SimulatedAnnealingSampler().sample(bqm, num_reads=5)",
                        "assert samples.first.sample['x'] in (0, 1)",
                        "print('dwave.samplers Colab smoke ok')",
                    ]
                ),
            ]
        )


def run_python_qci_setup_smoke() -> None:
    source = notebook_code(QCI_NOTEBOOK)
    required_snippets = (
        "eqc-models==0.19.0",
        "numpy>=1.26,<2",
        "networkx>=2.8,<3",
        "os.kill(os.getpid(), 9)",
        'subprocess.check_call(["idaes", "get-extensions", "--to", "./bin"])',
    )
    forbidden_snippets = (
        "!pip install eqc_models pyomo",
        "!pip install idaes-pse --pre",
    )

    missing = [snippet for snippet in required_snippets if snippet not in source]
    if missing:
        raise AssertionError(
            "QCI Colab setup is missing expected snippets: " + ", ".join(missing)
        )

    present = [snippet for snippet in forbidden_snippets if snippet in source]
    if present:
        raise AssertionError(
            "QCI Colab setup still contains unsafe install snippets: " + ", ".join(present)
        )

    print("QCI Colab setup policy ok")


def find_julia_executable(julia_executable: str | None, julia_version: str | None) -> str:
    if julia_executable:
        return julia_executable

    env = os.environ.copy()
    if julia_version:
        env["JULIA_VERSION"] = julia_version

    result = run([str(FIND_JULIA_SCRIPT)], env=env, capture_output=True)
    return result.stdout.strip()


def temporary_writable_depot_env(env: dict[str, str], tmp: str) -> dict[str, str]:
    smoke_env = env.copy()
    depot_path = smoke_env.get("JULIA_DEPOT_PATH")
    smoke_env["JULIA_DEPOT_PATH"] = os.pathsep.join(
        [
            str(Path(tmp) / "depot"),
            depot_path if depot_path else str(Path.home() / ".julia"),
            "",
        ]
    )
    smoke_env.setdefault("JULIA_PKG_PRECOMPILE_AUTO", "0")
    return smoke_env


def run_julia_colab_resolve_smoke(julia: str, env: dict[str, str]) -> None:
    with tempfile.TemporaryDirectory(prefix="quip-colab-julia-resolve-") as tmp:
        smoke_env = temporary_writable_depot_env(env, tmp)
        project_dir = Path(tmp) / "Project"
        project_dir.mkdir()
        (project_dir / "Project.toml").write_text("[deps]\n", encoding="utf-8")
        (project_dir / "Manifest.toml").write_text(
            'julia_version = "0.0.0"\nmanifest_format = "2.0"\n',
            encoding="utf-8",
        )

        code = "\n".join(
            [
                'include("./scripts/notebook_bootstrap.jl")',
                "using .QuIPNotebookBootstrap",
                "project_dir = ARGS[1]",
                f'delete!(ENV, "{ALLOW_VERSION_MISMATCH_ENV}")',
                "QuIPNotebookBootstrap.instantiate_project!(project_dir; precompile = false)",
                "manifest_version = QuIPNotebookBootstrap.manifest_julia_version(project_dir)",
                "if manifest_version != VERSION",
                '    error("Expected resolve smoke manifest Julia version $(VERSION), got $(manifest_version)")',
                "end",
                'println("Julia Colab resolve smoke ok")',
            ]
        )

        run([julia, "--project=./scripts", "-e", code, str(project_dir)], env=smoke_env)


def run_julia_colab_project_instantiate_smoke(
    julia: str,
    env: dict[str, str],
    notebook_projects: tuple[str, ...],
) -> None:
    for project in notebook_projects:
        source_project_dir = REPO_ROOT / "notebooks_jl" / "envs" / project
        with tempfile.TemporaryDirectory(prefix="quip-colab-julia-project-") as tmp:
            smoke_env = temporary_writable_depot_env(env, tmp)
            project_dir = Path(tmp) / project
            project_dir.mkdir()
            for name in ("Project.toml", "Manifest.toml"):
                shutil.copy2(source_project_dir / name, project_dir / name)

            code = "\n".join(
                [
                    'include("./scripts/notebook_bootstrap.jl")',
                    "using .QuIPNotebookBootstrap",
                    "project_dir = ARGS[1]",
                    f'delete!(ENV, "{ALLOW_VERSION_MISMATCH_ENV}")',
                    "QuIPNotebookBootstrap.instantiate_project!(project_dir; precompile = false)",
                    "manifest_version = QuIPNotebookBootstrap.manifest_julia_version(project_dir)",
                    "if manifest_version != VERSION",
                    '    error("Expected project smoke manifest Julia version $(VERSION), got $(manifest_version)")',
                    "end",
                    'println("Julia Colab project instantiate smoke ok for $(basename(project_dir))")',
                ]
            )

            run([julia, "--project=./scripts", "-e", code, str(project_dir)], env=smoke_env)


def run_julia_colab_mismatch_smoke(
    *,
    julia_executable: str | None,
    julia_version: str | None,
    notebook_projects: tuple[str, ...],
    instantiate_projects: tuple[str, ...],
) -> None:
    julia = find_julia_executable(julia_executable, julia_version)
    notebook_project_args = [
        str(REPO_ROOT / "notebooks_jl" / "envs" / project)
        for project in notebook_projects
    ]
    real_project_code = "\n".join(
        [
            'include("./scripts/notebook_bootstrap.jl")',
            "using .QuIPNotebookBootstrap",
            f'delete!(ENV, "{ALLOW_VERSION_MISMATCH_ENV}")',
            "for project_dir in ARGS",
            "    QuIPNotebookBootstrap.validate_project_julia_version!(project_dir; in_colab = true)",
            '    println("Julia Colab mismatch policy ok for $(basename(project_dir))")',
            "end",
        ]
    )

    env = os.environ.copy()
    env["COLAB_RELEASE_TAG"] = "local-test"
    run([julia, "--project=./scripts", "-e", real_project_code, *notebook_project_args], env=env)

    with tempfile.TemporaryDirectory(prefix="quip-colab-julia-") as tmp:
        project_dir = Path(tmp) / "Project"
        project_dir.mkdir()
        (project_dir / "Manifest.toml").write_text(
            'julia_version = "0.0.0"\nmanifest_format = "2.0"\n',
            encoding="utf-8",
        )

        code = "\n".join(
            [
                'include("./scripts/notebook_bootstrap.jl")',
                "using .QuIPNotebookBootstrap",
                "project_dir = ARGS[1]",
                f'delete!(ENV, "{ALLOW_VERSION_MISMATCH_ENV}")',
                "QuIPNotebookBootstrap.validate_project_julia_version!(project_dir; in_colab = true)",
                f'ENV["{ALLOW_VERSION_MISMATCH_ENV}"] = "0"',
                "try",
                "    QuIPNotebookBootstrap.validate_project_julia_version!(project_dir; in_colab = true)",
                '    error("Strict Colab mismatch validation unexpectedly passed")',
                "catch err",
                "    message = sprint(showerror, err)",
                f'    if !occursin("Set {ALLOW_VERSION_MISMATCH_ENV}=1", message)',
                "        rethrow()",
                "    end",
                "end",
                'println("Julia Colab mismatch smoke ok")',
            ]
        )

        run([julia, "--project=./scripts", "-e", code, str(project_dir)], env=env)

    run_julia_colab_resolve_smoke(julia, env)
    run_julia_colab_project_instantiate_smoke(julia, env, instantiate_projects)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run focused local smokes for Colab runtime failure modes."
    )
    parser.add_argument(
        "--python",
        default=sys.executable,
        help="Python executable used to create the temporary Ocean SDK environment.",
    )
    parser.add_argument(
        "--julia",
        default=os.environ.get("JULIA_BIN"),
        help="Julia executable used for the Colab mismatch smoke.",
    )
    parser.add_argument(
        "--julia-version",
        default=os.environ.get("COLAB_MISMATCH_JULIA_VERSION"),
        help="Julia version passed to scripts/find_julia.sh when --julia is unset.",
    )
    parser.add_argument(
        "--skip-python",
        action="store_true",
        help="Skip the fresh Ocean SDK Python smoke.",
    )
    parser.add_argument(
        "--skip-julia",
        action="store_true",
        help="Skip the Julia Colab mismatch smoke.",
    )
    parser.add_argument(
        "--julia-notebook-project",
        action="append",
        dest="julia_notebook_projects",
        choices=DEFAULT_JULIA_NOTEBOOK_PROJECTS,
        help=(
            "Notebook project env to validate in Colab mode. "
            "May be passed multiple times; defaults to all Julia Colab notebook projects."
        ),
    )
    parser.add_argument(
        "--julia-instantiate-project",
        action="append",
        dest="julia_instantiate_projects",
        choices=DEFAULT_JULIA_NOTEBOOK_PROJECTS,
        help=(
            "Notebook project env to instantiate in a temporary Colab-mode copy. "
            "May be passed multiple times; defaults to all Julia notebook projects."
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.skip_python and args.skip_julia:
        raise ValueError("At least one smoke must run.")

    if not args.skip_python:
        run_python_ocean_smoke(args.python)
        run_python_qci_setup_smoke()

    if not args.skip_julia:
        run_julia_colab_mismatch_smoke(
            julia_executable=args.julia,
            julia_version=args.julia_version,
            notebook_projects=tuple(args.julia_notebook_projects or DEFAULT_JULIA_NOTEBOOK_PROJECTS),
            instantiate_projects=tuple(
                args.julia_instantiate_projects or DEFAULT_JULIA_INSTANTIATE_PROJECTS
            ),
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
