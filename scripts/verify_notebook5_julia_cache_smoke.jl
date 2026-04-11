#!/usr/bin/env julia

include(joinpath(@__DIR__, "notebook_bootstrap.jl"))
using .QuIPNotebookBootstrap

QuIPNotebookBootstrap.instantiate_notebook_project("5-Benchmarking"; precompile = false)

using JSON

const TOTAL_READS = 8
const NOTEBOOK_PATH = normpath(joinpath(@__DIR__, "..", "notebooks_jl", "5-Benchmarking.ipynb"))
const HELPER_BLOCK_START = "const ANNEAL_CACHE_TAG ="
const HELPER_BLOCK_END = "# NOTEBOOK_5_BENCHMARK_HELPERS_END"

function notebook_helper_source(path::AbstractString = NOTEBOOK_PATH)
    notebook = JSON.parsefile(path)
    for cell in notebook["cells"]
        if get(cell, "cell_type", nothing) != "code"
            continue
        end

        source = join(get(cell, "source", String[]))
        if !occursin(HELPER_BLOCK_START, source) || !occursin(HELPER_BLOCK_END, source)
            continue
        end

        start_index = findfirst(HELPER_BLOCK_START, source)
        end_range = findfirst(HELPER_BLOCK_END, source)
        start_index === nothing && continue
        end_range === nothing && continue
        return source[first(start_index):last(end_range)]
    end

    error("Notebook 5 helper block markers were not found in $path.")
end

const NOTEBOOK_HELPER_SOURCE = notebook_helper_source()

function build_helper_module(output_dir::AbstractString; reads::Int)
    helpers = Module(:Notebook5CacheSmokeHelpers)
    Core.eval(helpers, :(using DWave))
    Core.eval(helpers, :(using JSON))
    Core.eval(helpers, :(using JuMP))
    Core.eval(helpers, :(using LinearAlgebra))
    Core.eval(helpers, :(using QUBO))
    Core.eval(helpers, :(using QUBOTools))
    Core.eval(helpers, :(using Random))
    Core.eval(helpers, :(using Statistics))
    Core.eval(helpers, :(using StatsBase))
    Core.eval(helpers, :(total_reads = $reads))
    Core.eval(helpers, :(pickle_path = $output_dir))
    Core.eval(
        helpers,
        :(to_float_vector(values) = Float64[Float64(v) for v in values]),
    )
    Base.include_string(helpers, NOTEBOOK_HELPER_SOURCE, NOTEBOOK_PATH)
    return helpers
end

call_helper(helpers::Module, name::Symbol, args...; kwargs...) =
    Base.invokelatest(getproperty(helpers, name), args...; kwargs...)

function main()
    mktempdir(prefix = "quip-notebook5-cache-smoke-") do tmpdir
        helpers = build_helper_module(tmpdir; reads = TOTAL_READS)
        _, _, instance_model = call_helper(helpers, :build_random_ising_instance, 7, 4)
        solution_name = joinpath(
            tmpdir,
            "solutions_7_geometric_5_$(helpers.ANNEAL_CACHE_TAG).json",
        )

        sol_miss, time_miss = call_helper(
            helpers,
            :load_or_generate_solution,
            instance_model,
            7,
            "geometric",
            5;
            overwrite_pickles = false,
        )
        isfile(solution_name) || error("Expected the Notebook 5 cache-smoke path to create $solution_name.")

        parsed = JSON.parsefile(solution_name)
        haskey(parsed, "energies") || error("Expected a cached `energies` field in $solution_name.")
        haskey(parsed, "occurrences") || error("Expected a cached `occurrences` field in $solution_name.")
        haskey(parsed, "time_s") || error("Expected a cached `time_s` field in $solution_name.")
        sum(Int(v) for v in parsed["occurrences"]) == TOTAL_READS ||
            error("Expected cached occurrences to sum to $TOTAL_READS reads.")

        parsed["energies"] = Any[91.25]
        parsed["occurrences"] = Any[TOTAL_READS]
        parsed["time_s"] = 123.456
        open(solution_name, "w") do io
            JSON.print(io, parsed)
        end

        sol_hit, time_hit = call_helper(
            helpers,
            :load_or_generate_solution,
            instance_model,
            7,
            "geometric",
            5;
            overwrite_pickles = false,
        )
        sol_miss.energies != sol_hit.energies ||
            error("Expected the second Notebook 5 cache-smoke call to load the modified cache entry.")
        sol_hit.energies == [91.25] || error("Expected the second Notebook 5 cache-smoke call to read cached energies.")
        sol_hit.occurrences == [TOTAL_READS] ||
            error("Expected the second Notebook 5 cache-smoke call to read cached occurrences.")
        time_miss != time_hit || error("Expected the second Notebook 5 cache-smoke call to use cached timing data.")
        time_hit == 123.456 || error("Expected the second Notebook 5 cache-smoke call to read the cached time.")
    end

    println("Notebook 5 Julia Neal-optimizer cache smoke ok")
    return nothing
end

main()
