import Pkg
import Tar
include(joinpath(@__DIR__, "notebook_bootstrap.jl"))
using .QuIPNotebookBootstrap

const WORKSPACE = abspath(joinpath(@__DIR__, ".."))
const DIST_PATH = abspath(joinpath(WORKSPACE, "dist"))
const NOTEBOOK = get(ENV, "NOTEBOOK", joinpath("notebooks_jl", "1-MathProg.ipynb"))
const PROJECT_DIR = QuIPNotebookBootstrap.notebook_project_dir(
    QuIPNotebookBootstrap.notebook_key(NOTEBOOK);
    repo_dir = WORKSPACE,
)

function get_last_tag()
    file_path = joinpath(WORKSPACE, "last.tag")

    if isfile(file_path)
        text = read(file_path, String)

        m = match(r"tag:\s*v(.*)", text)

        if isnothing(m)
            return nothing
        else
            return parse(VersionNumber, m[1])
        end
    else
        return nothing
    end
end

function get_next_tag()
    last_tag = get_last_tag()

    if isnothing(last_tag)
        return v"0.1.0"
    else
        return VersionNumber(
            last_tag.major,
            last_tag.minor,
            last_tag.patch + 1,
            last_tag.prerelease,
            last_tag.build,
        )
    end
end

function copy_project()
    cp(
        joinpath(PROJECT_DIR, "Project.toml"),
        joinpath(WORKSPACE, "sysimage", "Project.toml");
        force = true,
    )
end

function copy_manifest()
    manifest_path = joinpath(PROJECT_DIR, "Manifest.toml")
    output_path = joinpath(WORKSPACE, "sysimage", "Manifest.toml")

    if isfile(manifest_path)
        cp(manifest_path, output_path; force = true)
    elseif isfile(output_path)
        rm(output_path; force = true)
    end
end

function write_next_tag()
    next_tag = get_next_tag()

    file_path = joinpath(WORKSPACE, "next.tag")

    write(file_path, "v$next_tag")

    return nothing
end

function build_tarball()
    temp_path = abspath(Tar.create(joinpath(WORKSPACE, "sysimage")))
    run(`gzip -9 $temp_path`)
    file_path = mkpath(joinpath(DIST_PATH, "sysimage.tar.gz"))

    cp("$temp_path.gz", file_path; force = true)
    rm(temp_path; force = true)
    rm("$temp_path.gz"; force = true)

    return nothing
end

function main()
    write_next_tag()
    copy_project()
    copy_manifest()
    build_tarball()

    return nothing
end

main() # Here we go!
