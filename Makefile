.PHONY: setup-julia sysimage verify-notebooks verify-mathprog

UV ?= uv
UV_CACHE_DIR ?= $(CURDIR)/.uv-cache
JULIA_PKG_PRECOMPILE_AUTO ?= 0
JULIA ?= $(shell ./scripts/find_julia.sh)
JULIA_HOME_DEPOT ?= $(HOME)/.julia
JULIA_DEPOT_PATH ?= $(CURDIR)/.julia-depot:$(JULIA_HOME_DEPOT)

NOTEBOOKS ?= notebooks_py/1-MathProg_python.ipynb notebooks_jl/1-MathProg.ipynb

setup-julia:
	JULIA_DEPOT_PATH=$(JULIA_DEPOT_PATH) JULIA_PKG_PRECOMPILE_AUTO=$(JULIA_PKG_PRECOMPILE_AUTO) $(JULIA) --project=./notebooks_jl -e 'import Pkg; Pkg.resolve(); Pkg.instantiate()'

sysimage:
	$(JULIA) -e 'using InteractiveUtils; versioninfo()'
	JULIA_DEPOT_PATH=$(JULIA_DEPOT_PATH) JULIA_PKG_PRECOMPILE_AUTO=$(JULIA_PKG_PRECOMPILE_AUTO) $(JULIA) --project=./notebooks_jl -e 'import Pkg; Pkg.resolve(); Pkg.instantiate()'
	JULIA_DEPOT_PATH=$(JULIA_DEPOT_PATH) JULIA_PKG_PRECOMPILE_AUTO=$(JULIA_PKG_PRECOMPILE_AUTO) $(JULIA) --project=./scripts -e 'import Pkg; Pkg.resolve(); Pkg.instantiate()'
	JULIA_DEPOT_PATH=$(JULIA_DEPOT_PATH) $(JULIA) --project=./scripts --threads=auto ./scripts/create_sysimage.jl

verify-notebooks:
	UV_CACHE_DIR=$(UV_CACHE_DIR) $(UV) sync --group docs --group mathprog
	JULIA_DEPOT_PATH=$(JULIA_DEPOT_PATH) JULIA_PKG_PRECOMPILE_AUTO=$(JULIA_PKG_PRECOMPILE_AUTO) $(JULIA) --project=./notebooks_jl -e 'import Pkg; Pkg.resolve(); Pkg.instantiate()'
	JULIA_DEPOT_PATH=$(JULIA_DEPOT_PATH) JULIA_PKG_PRECOMPILE_AUTO=$(JULIA_PKG_PRECOMPILE_AUTO) $(JULIA) --project=./scripts -e 'import Pkg; Pkg.resolve(); Pkg.instantiate()'
	UV_CACHE_DIR=$(UV_CACHE_DIR) JULIA_BIN=$(JULIA) JULIA_DEPOT_PATH=$(JULIA_DEPOT_PATH) JULIA_PKG_PRECOMPILE_AUTO=$(JULIA_PKG_PRECOMPILE_AUTO) $(UV) run --group docs --group mathprog python ./scripts/verify_notebooks.py $(NOTEBOOKS)

verify-mathprog:
	$(MAKE) verify-notebooks NOTEBOOKS="notebooks_py/1-MathProg_python.ipynb notebooks_jl/1-MathProg.ipynb"
