using Pkg
Pkg.instantiate()
include(joinpath(@__DIR__, "notebook_bootstrap.jl"))
using .QuIPNotebookBootstrap
using PackageCompiler, Libdl, TOML

const NOTEBOOK = get(ENV, "NOTEBOOK", joinpath("notebooks_jl", "1-MathProg.ipynb"))
const PROJECT_DIR = QuIPNotebookBootstrap.notebook_project_dir(
    QuIPNotebookBootstrap.notebook_key(NOTEBOOK);
    repo_dir = normpath(joinpath(@__DIR__, "..")),
)
const SYSIMAGE_PATH = joinpath(@__DIR__, "..", "sysimage", "sysimage.$(Libdl.dlext)")
const PROJECT_TOML = TOML.parsefile(joinpath(PROJECT_DIR, "Project.toml"))

mkpath(dirname(SYSIMAGE_PATH))
const PACKAGES = sort!(collect(keys(get(PROJECT_TOML, "deps", Dict{String, Any}()))))

PackageCompiler.create_sysimage(
    PACKAGES;
    project       = PROJECT_DIR,
    sysimage_path = SYSIMAGE_PATH,
    cpu_target    = "generic;sandybridge,-xsaveopt,clone_all;haswell,-rdrnd,base(1)",
)
