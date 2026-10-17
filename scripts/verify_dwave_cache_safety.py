"""Exercise notebook cache controls without credentials or D-Wave network calls."""

from __future__ import annotations

import argparse
import ast
import json
import os
import subprocess
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]


def code_cells(path: Path) -> list[str]:
    notebook = json.loads(path.read_text(encoding="utf-8"))
    return ["".join(c["source"]) for c in notebook["cells"] if c["cell_type"] == "code"]


def python_cache_setup() -> str:
    imported_dwave = False
    for source in code_cells(ROOT / "notebooks_py/4-DWAVE_python.ipynb"):
        try:
            tree = ast.parse(source)
        except SyntaxError:  # IPython installation cells are not Python modules.
            continue
        for node in tree.body:
            if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("dwave"):
                imported_dwave = True
            if isinstance(node, ast.Import) and any(alias.name.startswith("dwave") for alias in node.names):
                imported_dwave = True
            if isinstance(node, ast.Assign) and any(
                ast.unparse(target) == "os.environ['DWAVE_CACHE_HOME']" for target in node.targets
            ):
                assert not imported_dwave, "Cache policy must precede D-Wave imports"
                return source
    raise AssertionError("Python notebook must disable persistent D-Wave caches in setup")


def python_sampler_options() -> list[dict[str, object]]:
    options = []
    for source in code_cells(ROOT / "notebooks_py/4-DWAVE_python.ipynb"):
        if "DWaveSampler(" not in source:
            continue
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "DWaveSampler":
                options.append({kw.arg: ast.literal_eval(kw.value) for kw in node.keywords})
    assert options, "No notebook QPU constructors were exercised"
    return options


def check_python() -> None:
    import diskcache
    import requests
    from dwave.cloud.auth.creds import Credentials
    from dwave.cloud.config import load_config
    from dwave.cloud.config.models import validate_config_v1
    from dwave.cloud.regions import get_regions
    from dwave.system import DWaveSampler

    calls = []

    def send(adapter, request, **kwargs):
        assert request.url.startswith("https://mock.invalid/"), request.url
        calls.append(request.url)
        response = requests.Response()
        response.status_code = 200
        response.request = request
        response.url = request.url
        if "/regions/" in request.url:
            payload = [dict(code="na-west-1", name="Test Region", endpoint="https://mock.invalid/sapi/v2/")]
            content_type = "application/vnd.dwave.metadata.regions+json; version=1.0"
        else:
            payload = [dict(
                identity=dict(name="mock-qpu", version=dict(graph_id="1")),
                status="ONLINE", description="mock", avg_load=0.0,
                properties=dict(
                    supported_problem_types=["ising", "qubo"], qubits=[0, 1],
                    couplers=[[0, 1]], num_qubits=2, category="qpu",
                    parameters={"num_reads": "reads"}, topology={"type": "chimera", "shape": [1, 1, 1]},
                ),
            )]
            content_type = "application/vnd.dwave.sapi.solver-definition-list+json; version=3.0.0"
        response.headers["Content-Type"] = content_type
        response._content = json.dumps(payload).encode()
        return response

    with (
        patch.dict(os.environ, {"DWAVE_CACHE_HOME": "/untrusted-cache", "DWAVE_CACHE_ENABLED": "true"}),
        patch.object(diskcache.Cache, "__init__", side_effect=AssertionError("Persistent cache accessed")),
        patch.object(Credentials, "__init__", side_effect=AssertionError("OAuth credentials accessed")),
        patch.object(requests.adapters.HTTPAdapter, "send", send),
    ):
        # Execute the real setup with Python already imported, as in a reused kernel.
        exec(compile(python_cache_setup(), "notebook cache setup", "exec"), {})
        assert os.environ["DWAVE_CACHE_HOME"] == "off"
        config = validate_config_v1(load_config(
            config_file=False, token="test-token", metadata_api_endpoint="https://mock.invalid/metadata/v1/",
        ))
        assert config.cache.enabled is False and config.cache.home is None
        assert len(get_regions(config)) == 1
        options = python_sampler_options()
        for kwargs in options:
            assert kwargs.get("cache_home") == "off"
            with DWaveSampler(config_file=False, token="test-token", endpoint="https://mock.invalid/sapi/v2/", **kwargs) as sampler:
                assert sampler.nodelist == [0, 1] and sampler.edgelist == [(0, 1)]
        assert len(calls) == 1 + 2 * len(options), calls
    print(f"Cache-free manual-token QPU smoke passed ({len(calls)} mocked HTTP requests)")


def check_julia(julia: str) -> None:
    cells = code_cells(ROOT / "notebooks_jl/4-DWave.ipynb")
    optimizer = [c for c in cells if "set_optimizer(qubo_model, DWave.Optimizer)" in c]
    direct = [c for c in cells if "sampler = DWave.dwave_system.DWaveSampler(" in c]
    assert len(optimizer) == len(direct) == 1
    # Run the actual cells with a recording bridge; paid optimize! is intentionally mocked.
    prelude = '''using Test
module DWave
    struct Sampler end
    struct Optimizer end
    const dwave_system = (
        DWaveSampler = (; kwargs...) -> (; kwargs...),
        EmbeddingComposite = sampler -> (child=sampler,),
    )
end
qubo_model = Dict{Any,Any}()
set_optimizer(model, optimizer) = nothing
set_optimizer_attribute(model, key, value) = (model[key] = value)
optimize!(model) = nothing
objective_value(model) = 0.0
ENV["DWAVE_API_TOKEN"] = "test-token"
'''
    assertions = '''
@test qubo_model[DWave.Sampler()].child.cache_home == "off"
@test qubo_model[DWave.Sampler()].child.token == "test-token"
@test qubo_model["num_reads"] == 1024
@test sampler.cache_home == "off"
@test sampler.token == "test-token"
println("Julia notebook cache-free sampler configuration passed")
'''
    subprocess.run([julia, "--startup-file=no", "-e", prelude + optimizer[0] + "\n" + direct[0] + assertions], check=True, timeout=60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--julia", help="Check Julia notebook cells with a recording bridge")
    args = parser.parse_args()
    if args.julia:
        check_julia(args.julia)
    else:
        check_python()
