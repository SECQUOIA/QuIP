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

4. To work on the mathematical programming Python notebook locally, install its
   Python dependencies into the same `uv` environment:

   ```bash
   uv sync --group mathprog
   ```

5. To prepare the shared Julia notebook environment locally, use the repo
   target instead of a bare `Pkg.instantiate()`:

   ```bash
   make setup-julia
   ```

   This disables Julia's automatic blanket precompile step while instantiating
   the shared `notebooks_jl` project. A plain command like
   `julia --project=./notebooks_jl -e 'import Pkg; Pkg.instantiate()'` may try
   to precompile unrelated packages such as `DWave`, `DWaveNeal`, `PythonPlot`,
   and `QUBO`, which are not needed for the math programming notebook and can
   fail depending on the local Conda/pixi state.

6. To verify notebook execution locally, use the repo targets:

   ```bash
   make verify-mathprog
   ```

   This executes the Python and Julia math programming notebooks through
   `jupyter nbconvert` and writes the executed copies to `.nbverify/`.
   The verification flow keeps the Python package cache in `.uv-cache/`, so it
   does not depend on writing to a global `uv` cache. Julia writes temporary
   package state to `.julia-depot/` while still reusing packages already
   available in `~/.julia/`.

   To verify a different set of notebooks, override `NOTEBOOKS`:

   ```bash
   make verify-notebooks NOTEBOOKS="notebooks_py/2-QUBO_python.ipynb notebooks_jl/2-QUBO.ipynb"
   ```

7. To run the notebooks interactively, install an IJulia kernel for this repo
   and then launch Jupyter:

   ```bash
   julia --project=./scripts -e 'import Pkg; Pkg.resolve(); Pkg.instantiate(); using IJulia; installkernel("QuIP Julia", "--project=$(abspath("notebooks_jl"))")'
   uv run --group docs jupyter lab
   ```

   The `docs` group includes `jupyterlab`, so the interactive launcher stays
   inside the same project-local `uv` environment used for the book build.

   Then select:

   - `Python 3` for notebooks under `notebooks_py/`
   - `QuIP Julia` or another Julia kernel for notebooks under `notebooks_jl/`

   If you see a Python `SyntaxError` on a line like
   `IN_COLAB = haskey(ENV, ...) || ...`, the Julia notebook is running with the
   wrong kernel.
