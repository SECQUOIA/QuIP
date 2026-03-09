# QuIP: Quantum Integer Programming Notebooks

This repository collects the Julia and Python lecture notebooks used for
quantum integer programming material. The repo now serves as the source for a
single Jupyter Book built from the repository root and published through GitHub
Pages.

The first book release is intentionally static. Notebook execution is disabled
in CI, several Python notebooks still lack committed outputs, and a broader
cleanup pass on content, environments, and notebook structure will happen after
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

The built site will be written to `_build/html/index.html`.
