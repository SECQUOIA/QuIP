.PHONY: setup-julia sysimage verify-notebooks verify-mathprog verify-qubo-python verify-julia-colab verify-julia-colab-notebooks verify-julia-colab-smokes verify-julia-notebook5-cache-smoke install-julia-colab-hook

UV ?= uv
UV_CACHE_DIR ?= $(CURDIR)/.uv-cache
UV_GROUP_FLAGS ?= --group docs --group mathprog
JULIA_PKG_PRECOMPILE_AUTO ?= 0
JULIA_VERSION ?= 1.11.5
JULIA ?= $(shell JULIA_VERSION=$(JULIA_VERSION) ./scripts/find_julia.sh)
JULIA_HOME_DEPOT ?= $(HOME)/.julia
JULIA_DEPOT_PATH ?= $(CURDIR)/.julia-depot:$(JULIA_HOME_DEPOT)
COLAB_JULIA_VERSION ?= 1.11.9
ifneq ($(filter command line environment override,$(origin JULIA)),)
COLAB_JULIA ?= $(JULIA)
else
COLAB_JULIA ?= $(shell JULIA_VERSION=$(COLAB_JULIA_VERSION) ./scripts/find_julia.sh)
endif
COLAB_JULIA_DEPOT_PATH ?= $(CURDIR)/.julia-colab-depot:$(JULIA_HOME_DEPOT)
COLAB_UV_GROUP_FLAGS ?= --group docs --group mathprog --group qubo
COLAB_JULIA_NOTEBOOKS ?= notebooks_jl/1-MathProg.ipynb notebooks_jl/2-QUBO.ipynb
COLAB_JULIA_SMOKE_NOTEBOOKS ?= 3-GAMA 4-DWave 5-Benchmarking

NOTEBOOK ?= notebooks_jl/1-MathProg.ipynb
SYSIMAGE_NOTEBOOK ?=
NOTEBOOKS ?= notebooks_py/1-MathProg_python.ipynb notebooks_jl/1-MathProg.ipynb

setup-julia:
	JULIA_DEPOT_PATH=$(JULIA_DEPOT_PATH) JULIA_PKG_PRECOMPILE_AUTO=$(JULIA_PKG_PRECOMPILE_AUTO) $(JULIA) --project=./scripts -e 'include("./scripts/notebook_bootstrap.jl"); using .QuIPNotebookBootstrap; QuIPNotebookBootstrap.instantiate_scripts_project(precompile=false)'
	JULIA_DEPOT_PATH=$(JULIA_DEPOT_PATH) JULIA_PKG_PRECOMPILE_AUTO=$(JULIA_PKG_PRECOMPILE_AUTO) $(JULIA) --project=./scripts -e 'include("./scripts/notebook_bootstrap.jl"); using .QuIPNotebookBootstrap; QuIPNotebookBootstrap.instantiate_notebook_project(ARGS[1])' "$(NOTEBOOK)"

sysimage:
	$(JULIA) -e 'using InteractiveUtils; versioninfo()'
	JULIA_DEPOT_PATH=$(JULIA_DEPOT_PATH) JULIA_PKG_PRECOMPILE_AUTO=$(JULIA_PKG_PRECOMPILE_AUTO) $(JULIA) --project=./scripts -e 'import Pkg; Pkg.instantiate()'
	JULIA_DEPOT_PATH=$(JULIA_DEPOT_PATH) JULIA_PKG_PRECOMPILE_AUTO=$(JULIA_PKG_PRECOMPILE_AUTO) SYSIMAGE_NOTEBOOK="$(SYSIMAGE_NOTEBOOK)" $(JULIA) --project=./scripts -e 'include("./scripts/notebook_bootstrap.jl"); using .QuIPNotebookBootstrap; QuIPNotebookBootstrap.instantiate_sysimage_project(get(ENV, "SYSIMAGE_NOTEBOOK", nothing))'
	JULIA_DEPOT_PATH=$(JULIA_DEPOT_PATH) NOTEBOOK="$(SYSIMAGE_NOTEBOOK)" $(JULIA) --project=./scripts --threads=auto ./scripts/create_sysimage.jl

verify-notebooks:
	UV_CACHE_DIR=$(UV_CACHE_DIR) $(UV) sync $(UV_GROUP_FLAGS)
	UV_CACHE_DIR=$(UV_CACHE_DIR) JULIA_DEPOT_PATH=$(JULIA_DEPOT_PATH) JULIA_PKG_PRECOMPILE_AUTO=$(JULIA_PKG_PRECOMPILE_AUTO) $(UV) run $(UV_GROUP_FLAGS) python ./scripts/verify_notebooks.py $(NOTEBOOKS)

verify-mathprog:
	$(MAKE) verify-notebooks UV_GROUP_FLAGS="--group docs --group mathprog" NOTEBOOKS="notebooks_py/1-MathProg_python.ipynb notebooks_jl/1-MathProg.ipynb"

verify-qubo-python:
	$(MAKE) verify-notebooks UV_GROUP_FLAGS="--group docs --group qubo" NOTEBOOKS="notebooks_py/2-QUBO_python.ipynb"

verify-julia-colab:
	$(MAKE) verify-julia-colab-notebooks
	$(MAKE) verify-julia-colab-smokes
	$(MAKE) verify-julia-notebook5-cache-smoke

verify-julia-colab-notebooks:
	UV_CACHE_DIR=$(UV_CACHE_DIR) $(UV) sync $(COLAB_UV_GROUP_FLAGS)
	UV_CACHE_DIR=$(UV_CACHE_DIR) JULIA_DEPOT_PATH=$(COLAB_JULIA_DEPOT_PATH) JULIA_PKG_PRECOMPILE_AUTO=$(JULIA_PKG_PRECOMPILE_AUTO) $(UV) run $(COLAB_UV_GROUP_FLAGS) python ./scripts/verify_notebooks.py $(COLAB_JULIA_NOTEBOOKS)

verify-julia-colab-smokes:
	UV_CACHE_DIR=$(UV_CACHE_DIR) $(UV) sync $(COLAB_UV_GROUP_FLAGS)
	JULIA_BIN=$(COLAB_JULIA) JULIA_DEPOT_PATH=$(COLAB_JULIA_DEPOT_PATH) JULIA_PKG_PRECOMPILE_AUTO=$(JULIA_PKG_PRECOMPILE_AUTO) $(COLAB_JULIA) --project=./scripts ./scripts/verify_julia_env_smokes.jl $(COLAB_JULIA_SMOKE_NOTEBOOKS)

verify-julia-notebook5-cache-smoke:
	UV_CACHE_DIR=$(UV_CACHE_DIR) $(UV) sync $(COLAB_UV_GROUP_FLAGS)
	JULIA_BIN=$(COLAB_JULIA) JULIA_DEPOT_PATH=$(COLAB_JULIA_DEPOT_PATH) JULIA_PKG_PRECOMPILE_AUTO=$(JULIA_PKG_PRECOMPILE_AUTO) $(COLAB_JULIA) --project=./scripts ./scripts/verify_notebook5_julia_cache_smoke.jl

install-julia-colab-hook:
	chmod +x .githooks/pre-commit
	git config core.hooksPath .githooks
