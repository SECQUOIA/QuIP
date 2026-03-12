#!/usr/bin/env julia

include(joinpath(@__DIR__, "notebook_bootstrap.jl"))
using .QuIPNotebookBootstrap

function notebook_key(target::AbstractString)
    return QuIPNotebookBootstrap.notebook_key(target)
end

function run_smoke(target::AbstractString)
    key = notebook_key(target)
    import_expr = QuIPNotebookBootstrap.notebook_import_expr(key)
    if import_expr === nothing
        error("No import smoke is defined for notebook `$key`.")
    end

    QuIPNotebookBootstrap.instantiate_notebook_project(target)
    Core.eval(Main, import_expr)
    println("$key imports ok")
    return nothing
end

function main(args)
    targets = isempty(args) ? ["3-GAMA", "4-DWave", "5-Benchmarking"] : args
    for target in targets
        run_smoke(target)
    end
    return nothing
end

main(ARGS)
