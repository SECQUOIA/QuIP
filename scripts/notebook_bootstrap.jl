module QuIPNotebookBootstrap

using Dates
using Logging
import Pkg

const WORKSPACE = normpath(joinpath(@__DIR__, ".."))
const NOTEBOOKS_DIRNAME = "notebooks_jl"
const NOTEBOOK_ENVS_DIRNAME = "envs"
const PYTHON_STACK_NOTEBOOKS = Set((
    "2-QUBO",
    "3-GAMA",
    "4-DWave",
    "5-Benchmarking",
))
const NOTEBOOK_IMPORTS = Dict(
    "1-MathProg" => :(using Plots, JuMP, GLPK, HiGHS, Ipopt, SpecialFunctions, AmplNLWriter, Bonmin_jll, Couenne_jll, SCIP),
    "2-QUBO" => :(using Karnak, LinearAlgebra, Graphs, JuMP, QUBO, Plots, HiGHS, DWave, Luxor, QUBOTools, ToQUBO),
    "3-GAMA" => :(using BinaryWrappers, DelimitedFiles, NPZ, JuMP, DWave, LinearAlgebra, Measures, Random, Plots, StatsBase, StatsPlots, lib4ti2_jll),
    "4-DWave" => :(using LinearAlgebra, Plots, JuMP, QUBO, DWave, Graphs, QUBOTools),
    "5-Benchmarking" => :(using JuMP, QUBO, LinearAlgebra, Plots, DWave, Random, Statistics, QUBOTools),
)

timestamp() = Dates.format(now(), "HH:MM:SS")

function log_step(message::AbstractString)
    println("[$(timestamp())] $message")
    flush(stdout)
    return nothing
end

function detect_colab()
    return haskey(ENV, "COLAB_RELEASE_TAG") ||
        haskey(ENV, "COLAB_JUPYTER_IP") ||
        isdir(joinpath("/content", "sample_data"))
end

function env_bool(name::AbstractString)
    value = get(ENV, name, nothing)
    value === nothing && return nothing

    normalized = lowercase(strip(value))
    if normalized in ("1", "true", "yes", "on")
        return true
    elseif normalized in ("0", "false", "no", "off")
        return false
    end

    error("Expected `$name` to be one of 1/0/true/false/yes/no/on/off, got `$value`.")
end

default_bootstrap_warm_packages(; in_colab::Bool = detect_colab()) =
    something(env_bool("QUIP_NOTEBOOK_WARM_PACKAGES"), in_colab)

default_bootstrap_precompile(;
    in_colab::Bool = detect_colab(),
    warm_packages::Bool = default_bootstrap_warm_packages(in_colab = in_colab),
) = in_colab && !warm_packages

function notebook_key(target::AbstractString)
    return splitext(basename(target))[1]
end

function notebook_requires_python(project_key::AbstractString)
    return project_key in PYTHON_STACK_NOTEBOOKS
end

notebook_import_expr(project_key::AbstractString) = get(NOTEBOOK_IMPORTS, project_key, nothing)

function notebook_project_dir(project_key::AbstractString; repo_dir::AbstractString = WORKSPACE)
    return joinpath(repo_dir, NOTEBOOKS_DIRNAME, NOTEBOOK_ENVS_DIRNAME, project_key)
end

function candidate_repo_dirs(; cwd::AbstractString = pwd())
    return unique((
        normpath(cwd),
        normpath(cwd, ".."),
        normpath(cwd, "QuIP"),
        normpath(cwd, "..", "QuIP"),
        normpath("/content", "QuIP"),
        WORKSPACE,
    ))
end

function is_repo_root(path::AbstractString)
    return isfile(joinpath(path, "scripts", "notebook_bootstrap.jl")) &&
        isdir(joinpath(path, NOTEBOOKS_DIRNAME, NOTEBOOK_ENVS_DIRNAME))
end

function find_repo_root(; cwd::AbstractString = pwd())
    for candidate in candidate_repo_dirs(cwd = cwd)
        if is_repo_root(candidate)
            return normpath(candidate)
        end
    end
    return nothing
end

function ensure_repo_root(; in_colab::Bool = detect_colab())
    repo_dir = find_repo_root()
    if repo_dir !== nothing
        return repo_dir
    end

    if !in_colab
        error("Could not locate the QuIP repository root from $(pwd()).")
    end

    repo_dir = get(ENV, "QUIP_REPO_DIR", joinpath(pwd(), "QuIP"))
    if !isdir(repo_dir)
        log_step("Cloning SECQUOIA/QuIP into $repo_dir")
        run(`git clone --depth 1 https://github.com/SECQUOIA/QuIP.git $repo_dir`)
    else
        log_step("Using existing QuIP clone at $repo_dir")
    end

    if !is_repo_root(repo_dir)
        error("The repository at $repo_dir does not contain the expected Julia notebook bootstrap files.")
    end

    ENV["QUIP_REPO_DIR"] = normpath(repo_dir)
    return normpath(repo_dir)
end

function configure_python_runtime!(
    repo_dir::AbstractString;
    in_colab::Bool = detect_colab(),
    python_packages::Vector{String} = ["dwave-ocean-sdk"],
)
    ENV["JULIA_CONDAPKG_BACKEND"] = "Null"

    if in_colab
        if !isempty(python_packages)
            log_step("Installing Python packages: $(join(python_packages, ", "))")
            run(`python3 -m pip install -q $(python_packages...)`)
        end
        python_exe = something(Sys.which("python3"), "python3")
    else
        python_exe = joinpath(repo_dir, ".venv", "bin", "python3")
        if !isfile(python_exe)
            error("Could not find $python_exe. Run `uv sync --group qubo` from the repository root before launching this notebook.")
        end
    end

    ENV["JULIA_PYTHONCALL_EXE"] = python_exe
    log_step("Using Python runtime: $python_exe")
    return python_exe
end

function activate_project!(project_dir::AbstractString)
    log_step("Activating project at `$project_dir`")
    Pkg.activate(project_dir)
    return nothing
end

function instantiate_project!(project_dir::AbstractString; precompile::Bool = true)
    activate_project!(project_dir)
    log_step("Instantiating Julia packages")
    @time Pkg.instantiate()
    if precompile
        log_step("Precompiling Julia packages")
        @time Pkg.precompile()
    end
    return nothing
end

function warm_notebook_packages!(
    project_key::AbstractString;
    suppress_logs::Bool = true,
)
    import_expr = notebook_import_expr(project_key)
    import_expr === nothing && return false

    log_step("Loading notebook packages")
    if suppress_logs
        with_logger(NullLogger()) do
            Core.eval(Main, import_expr)
        end
    else
        Core.eval(Main, import_expr)
    end
    return true
end

function bootstrap_notebook(
    project_key::AbstractString;
    needs_python::Bool = notebook_requires_python(project_key),
    python_packages::Vector{String} = ["dwave-ocean-sdk"],
    warm_packages::Bool = default_bootstrap_warm_packages(),
    precompile::Bool = default_bootstrap_precompile(in_colab = detect_colab(), warm_packages = warm_packages),
    suppress_warmup_logs::Bool = warm_packages,
    chdir_to_notebooks::Bool = true,
)
    in_colab = detect_colab()
    repo_dir = ensure_repo_root(in_colab = in_colab)
    notebooks_dir = joinpath(repo_dir, NOTEBOOKS_DIRNAME)
    project_dir = notebook_project_dir(project_key; repo_dir = repo_dir)

    if !isdir(project_dir)
        error("Notebook project `$project_key` was not found at $project_dir.")
    end

    log_step("Notebook project key: $project_key")
    log_step("Google Colab runtime detected: $(in_colab)")

    if needs_python
        configure_python_runtime!(repo_dir; in_colab = in_colab, python_packages = python_packages)
    end

    instantiate_project!(project_dir; precompile = precompile)
    if warm_packages
        warm_notebook_packages!(project_key; suppress_logs = suppress_warmup_logs)
    end

    if chdir_to_notebooks
        cd(notebooks_dir)
        log_step("Working directory set to $notebooks_dir")
    end

    log_step("Notebook bootstrap complete")
    return (
        repo_dir = repo_dir,
        notebooks_dir = notebooks_dir,
        project_dir = project_dir,
        in_colab = in_colab,
    )
end

function instantiate_notebook_project(
    target::AbstractString;
    precompile::Bool = false,
    needs_python::Bool = notebook_requires_python(notebook_key(target)),
)
    project_key = notebook_key(target)
    repo_dir = ensure_repo_root(in_colab = false)
    project_dir = notebook_project_dir(project_key; repo_dir = repo_dir)

    if needs_python
        configure_python_runtime!(repo_dir; in_colab = false, python_packages = String[])
    end

    instantiate_project!(project_dir; precompile = precompile)
    return project_dir
end

end
