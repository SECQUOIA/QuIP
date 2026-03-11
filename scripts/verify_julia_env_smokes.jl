#!/usr/bin/env julia

include(joinpath(@__DIR__, "notebook_bootstrap.jl"))
using .QuIPNotebookBootstrap

const IMPORT_SMOKES = Dict(
    "1-MathProg" => :(using Plots, JuMP, GLPK, HiGHS, Ipopt, SpecialFunctions, AmplNLWriter, Bonmin_jll, Couenne_jll, SCIP),
    "2-QUBO" => :(using Karnak, LinearAlgebra, Graphs, JuMP, QUBO, Plots, HiGHS, DWave, Luxor, QUBOTools, ToQUBO),
    "3-GAMA" => :(using BinaryWrappers, DelimitedFiles, NPZ, JuMP, DWave, LinearAlgebra, Measures, Random, Plots, StatsBase, StatsPlots, lib4ti2_jll),
    "4-DWave" => :(using LinearAlgebra, Plots, JuMP, QUBO, DWave, Graphs, QUBOTools),
    "5-Benchmarking" => :(using JuMP, QUBO, LinearAlgebra, Plots, DWave, Random, Statistics, QUBOTools),
)

function notebook_key(target::AbstractString)
    return QuIPNotebookBootstrap.notebook_key(target)
end

function run_smoke(target::AbstractString)
    key = notebook_key(target)
    if !haskey(IMPORT_SMOKES, key)
        error("No import smoke is defined for notebook `$key`.")
    end

    QuIPNotebookBootstrap.instantiate_notebook_project(target)
    Core.eval(Main, IMPORT_SMOKES[key])
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
