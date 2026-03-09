# QuIP: Quantum Integer Programming Notebooks

By David E. Bernal Neira  
Davidson School of Chemical Engineering, Purdue University

This repository collects the Julia and Python lecture notebooks used for
quantum integer programming material. It serves as the source for a single
Jupyter Book built from the repository root and published through GitHub Pages.

This first book release is intentionally static. Notebook execution is disabled
in CI, several Python notebooks still lack committed outputs, and a broader
cleanup pass on content, environments, and notebook structure will follow after
the book scaffold is in place.

## Notebook map

| Topic | Python | Julia |
| --- | --- | --- |
| Mathematical Programming | [1-MathProg_python.ipynb](notebooks_py/1-MathProg_python.ipynb) | [1-MathProg.ipynb](notebooks_jl/1-MathProg.ipynb) |
| QUBO | [2-QUBO_python.ipynb](notebooks_py/2-QUBO_python.ipynb) | [2-QUBO.ipynb](notebooks_jl/2-QUBO.ipynb) |
| GAMA | [3-GAMA_python.ipynb](notebooks_py/3-GAMA_python.ipynb) | [3-GAMA.ipynb](notebooks_jl/3-GAMA.ipynb) |
| D-Wave | [4-DWAVE_python.ipynb](notebooks_py/4-DWAVE_python.ipynb) | [4-DWave.ipynb](notebooks_jl/4-DWave.ipynb) |
| Benchmarking | [5-Benchmarking_python.ipynb](notebooks_py/5-Benchmarking_python.ipynb) | [5-Benchmarking.ipynb](notebooks_jl/5-Benchmarking.ipynb) |
| QCi | [6-QCi_python.ipynb](notebooks_py/6-QCi_python.ipynb) | - |

## Local book build

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

   Then select:

   - `Python 3` for notebooks under `notebooks_py/`
   - `QuIP Julia` or another Julia kernel for notebooks under `notebooks_jl/`

   If you see a Python `SyntaxError` on a line like
   `IN_COLAB = haskey(ENV, ...) || ...`, the Julia notebook is running with the
   wrong kernel.

The built site will be written to `_build/html/index.html`.
