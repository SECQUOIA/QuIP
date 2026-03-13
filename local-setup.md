# Local Setup

This page collects repository-facing instructions for building the book and
running the notebooks locally.

## Book Build

This repository uses `uv` for Python environment management. The book build and
Python notebook tooling should be installed into the project virtual
environment, not into the root Python installation.

1. Create and sync the docs environment from the repository root:

   ```bash
   uv sync --group docs
   ```

   This creates a project-local `.venv` and leaves the root Python
   installation unchanged.

2. Confirm the Node.js toolchain used by Jupyter Book 2 is available:

   ```bash
   node --version
   npm --version
   ```

3. Build the site from the repository root:

   ```bash
   uv run --group docs jupyter book build --html --ci
   ```

The built site will be written to `_build/html/index.html`.

## Notebook Execution

4. To work on the Python notebooks locally, install the notebook-specific
   dependencies into the same `uv` environment:

   ```bash
   # For only the math programming notebooks:
   uv sync --group mathprog

   # For only the QUBO-related notebooks:
   uv sync --group qubo

   # To make both math programming and QUBO notebooks runnable together:
   uv sync --group mathprog --group qubo
   ```

   Use `mathprog` for [notebooks_py/1-MathProg_python.ipynb](notebooks_py/1-MathProg_python.ipynb) and `qubo` for [notebooks_py/2-QUBO_python.ipynb](notebooks_py/2-QUBO_python.ipynb) plus the Julia notebooks that rely on the D-Wave Python stack: [notebooks_jl/2-QUBO.ipynb](notebooks_jl/2-QUBO.ipynb), [notebooks_jl/3-GAMA.ipynb](notebooks_jl/3-GAMA.ipynb), [notebooks_jl/4-DWave.ipynb](notebooks_jl/4-DWave.ipynb), and [notebooks_jl/5-Benchmarking.ipynb](notebooks_jl/5-Benchmarking.ipynb). Those Julia notebooks reuse the repo-local Python environment instead of relying on Julia's `CondaPkg` resolver.

5. To prepare a Julia notebook environment locally, instantiate the
   notebook-specific project instead of a shared `notebooks_jl` project:

   ```bash
   make setup-julia NOTEBOOK=notebooks_jl/1-MathProg.ipynb
   make setup-julia NOTEBOOK=notebooks_jl/2-QUBO.ipynb
   ```

   This instantiates only the Julia project that belongs to the selected
   notebook under `notebooks_jl/envs/<notebook-stem>/`, so the math
   programming notebook no longer pays the D-Wave/QUBO dependency cost.

6. To verify notebook execution locally, use the repo targets:

   ```bash
   make verify-mathprog
   make verify-qubo-python
   ```

   `make verify-mathprog` executes the Python and Julia math programming
   notebooks through `jupyter nbconvert`, while `make verify-qubo-python`
   executes the Python QUBO notebook. Both write the executed copies to
   `.nbverify/`.
   The Julia notebook checks default to Julia `1.11.5` so they match the
   notebook manifests and the current Colab runtime; install it once with
   `juliaup add 1.11.5`, or override `JULIA=/path/to/julia` if you need a
   different compatible local binary.
   The verification flow keeps the Python package cache in `.uv-cache/`, so it
   does not depend on writing to a global `uv` cache. Julia writes temporary
   package state to `.julia-depot/` while still reusing packages already
   available in `~/.julia/`.

   To verify a different set of notebooks, override `NOTEBOOKS`:

   ```bash
   make verify-notebooks NOTEBOOKS="notebooks_py/2-QUBO_python.ipynb notebooks_jl/2-QUBO.ipynb"
   ```

   To approximate Google Colab's Julia runtime locally, first install Julia
   `1.11.5` once with `juliaup add 1.11.5`, then run the Colab-style Julia
   check:

   ```bash
   make verify-julia-colab
   ```

   This target uses `COLAB_JULIA` by default. If you set
   `JULIA=/path/to/julia` to a compatible binary on the command line, the
   Colab-style target will now reuse that binary unless you override
   `COLAB_JULIA` explicitly. You can also pick a specific juliaup toolchain
   with `COLAB_JULIA_VERSION=1.11.5`.
   This target writes Julia state into
   `.julia-colab-depot/1.11.5`, reuses registries and cached packages from
   `~/.julia` when available, executes the Julia math programming and QUBO
   notebooks end to end, and runs import/bootstrap smokes for the remaining
   Julia notebooks. It is the recommended local check before changing the
   Julia notebook bootstrap or notebook-specific Julia environments.

   To force a colder check that does not fall back to `~/.julia`, override the
   depot path explicitly:

   ```bash
   make verify-julia-colab COLAB_JULIA_DEPOT_PATH="$PWD/.julia-colab-depot/1.11.5"
   ```

   The Colab bootstrap now validates the running Julia patch version against the
   checked-in manifest before instantiating packages. If you intentionally want
   to allow a mismatch and accept a slower `Pkg` re-resolve, set
   `QUIP_ALLOW_JULIA_VERSION_MISMATCH=1` before launching the notebook.

   If you need the Colab bootstrap to clone a non-default QuIP ref, set
   `QUIP_REPO_REF=<branch-tag-or-40-char-commit>` before running the first
   Julia notebook cell.

   The default `make sysimage` build now uses the shared
   `notebooks_jl/envs/sysimage` project so the release artifact covers the full
   notebook stack. To build a notebook-specific sysimage instead, pass
   `SYSIMAGE_NOTEBOOK=notebooks_jl/2-QUBO.ipynb`.

   To install an optional git hook that runs this check when staged changes
   touch the Julia notebooks or their shared tooling, run:

   ```bash
   make install-julia-colab-hook
   ```

   The hook is a local `pre-commit` hook under `.githooks/pre-commit`. Set
   `SKIP_JULIA_COLAB_HOOK=1` for a one-off bypass.

7. To run the notebooks interactively, install a generic QuIP Julia kernel and
   then launch Jupyter:

   ```bash
   julia --project=./scripts -e 'import Pkg; Pkg.instantiate(); using IJulia; installkernel("QuIP Julia", "--project=$(abspath("scripts"))")'
   uv run --group docs jupyter lab
   ```

   The `docs` group includes `jupyterlab`, so the interactive launcher stays
   inside the same project-local `uv` environment used for the book build.

   Then select:

   - `Python 3` for notebooks under `notebooks_py/`
   - `QuIP Julia 1.12`, `QuIP Julia`, or another Julia kernel for notebooks
     under `notebooks_jl/`

   If you see a Python `SyntaxError` on a line like
   `IN_COLAB = haskey(ENV, ...) || ...`, the Julia notebook is running with the
   wrong kernel. The first Julia cell will activate the notebook-specific
   project under `notebooks_jl/envs/`, so one local Julia kernel is enough for
   all Julia notebooks.
