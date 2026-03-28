#!/usr/bin/env julia

include(joinpath(@__DIR__, "notebook_bootstrap.jl"))
using .QuIPNotebookBootstrap

QuIPNotebookBootstrap.instantiate_notebook_project("5-Benchmarking"; precompile = false)

using DWave
using JSON
using JuMP
using QUBO
using QUBOTools

const TOTAL_READS = 8
const ANNEAL_CACHE_TAG = "cache_smoke_v1"

solution_energies(sol) = hasproperty(sol, :energies) ? Float64[Float64(v) for v in sol.energies] : Float64.(QUBOTools.value.(sol))
solution_occurrences(sol) = hasproperty(sol, :occurrences) ? Int[Int(v) for v in sol.occurrences] : Int.(QUBOTools.reads.(sol))

function build_test_model(J, h)
    n = length(h)
    model = Model()
    @variable(model, s[1:n], Spin)
    @objective(model, Min, s' * J * s + h' * s)
    return model
end

function neal_sample_ising(instance_model, schedule, sweep, seed)
    set_optimizer(instance_model, DWave.Neal.Optimizer)
    set_attribute(instance_model, "num_reads", TOTAL_READS)
    set_attribute(instance_model, "num_sweeps", sweep)
    set_attribute(instance_model, "beta_schedule_type", schedule)
    set_attribute(instance_model, "seed", seed)

    start_time = time()
    optimize!(instance_model)
    time_s = time() - start_time
    sol = QUBOTools.solution(unsafe_backend(instance_model))
    return (
        energies = solution_energies(sol),
        occurrences = solution_occurrences(sol),
    ), time_s
end

function load_or_generate_solution(output_dir, instance_seed, schedule, sweep, instance_model; overwrite_pickles = false)
    solution_name = joinpath(
        output_dir,
        "solutions_$(instance_seed)_$(schedule)_$(sweep)_$(ANNEAL_CACHE_TAG).json",
    )

    if isfile(solution_name) && !overwrite_pickles
        cache = JSON.parsefile(solution_name)
        sol = (
            energies = Float64[Float64(v) for v in cache["energies"]],
            occurrences = Int[Int(v) for v in cache["occurrences"]],
        )
        return sol, Float64(cache["time_s"]), :cache_hit, solution_name
    end

    sol, time_s = neal_sample_ising(instance_model, schedule, sweep, 1729)
    open(solution_name, "w") do io
        JSON.print(io, Dict(
            "energies" => sol.energies,
            "occurrences" => sol.occurrences,
            "time_s" => time_s,
        ))
    end

    return sol, time_s, :cache_miss, solution_name
end

function main()
    J = [
        0.0  1.0 -1.0  0.0;
        0.0  0.0  1.0 -1.0;
        0.0  0.0  0.0  1.0;
        0.0  0.0  0.0  0.0;
    ]
    h = [0.5, -0.25, 0.75, -0.5]
    instance_model = build_test_model(J, h)

    mktempdir(prefix = "quip-notebook5-cache-smoke-") do tmpdir
        sol_miss, _, miss_status, solution_name = load_or_generate_solution(
            tmpdir,
            7,
            "geometric",
            5,
            instance_model,
        )
        miss_status == :cache_miss || error("Expected the first Notebook 5 cache-smoke call to miss the cache.")
        isfile(solution_name) || error("Expected the Notebook 5 cache-smoke path to create $solution_name.")

        parsed = JSON.parsefile(solution_name)
        haskey(parsed, "energies") || error("Expected a cached `energies` field in $solution_name.")
        haskey(parsed, "occurrences") || error("Expected a cached `occurrences` field in $solution_name.")
        haskey(parsed, "time_s") || error("Expected a cached `time_s` field in $solution_name.")
        sum(Int(v) for v in parsed["occurrences"]) == TOTAL_READS ||
            error("Expected cached occurrences to sum to $TOTAL_READS reads.")

        sol_hit, _, hit_status, _ = load_or_generate_solution(
            tmpdir,
            7,
            "geometric",
            5,
            instance_model,
        )
        hit_status == :cache_hit || error("Expected the second Notebook 5 cache-smoke call to hit the cache.")
        sol_hit.energies == sol_miss.energies || error("Cache-hit energies did not match the cache-miss result.")
        sol_hit.occurrences == sol_miss.occurrences ||
            error("Cache-hit occurrences did not match the cache-miss result.")
    end

    println("Notebook 5 Julia Neal-optimizer cache smoke ok")
    return nothing
end

main()
