# QuIP: Quantum Integer Programming Notebooks

This repository contains the Julia and Python notebooks used for the QuIP
lecture material, together with the Jupyter Book build that publishes them as a
website.

## Links

- Published book: <https://secquoia.github.io/QuIP/>
- Book homepage source: [index.md](index.md)
- Local build and execution instructions: [local-setup.md](local-setup.md)

## Repository Layout

- `notebooks_py/`: Python notebooks
- `notebooks_jl/`: Julia notebooks
- `scripts/`: helper scripts for local Julia/Jupyter workflows
- `myst.yml` and `_config.yml`: book configuration

Notebook-level author attributions remain inside the notebooks themselves. The
book homepage and site-level metadata are managed separately from this GitHub
README.

## Dependency security updates

Dependabot opens grouped security-update PRs for the maintained dependency
manifests and security updates for GitHub Actions. Routine version-update PRs
are disabled. Archived results and vendored source snapshots are excluded.

A separate workflow merges same-repository Dependabot PRs into the default
branch only after every required PR CI job and all reported checks succeed,
with no blocking reviews or unresolved review threads. It verifies the current
head SHA, retries temporary unknown mergeability, and never executes PR code
with write credentials. GitHub deletes merged branches automatically.

Merges made with `GITHUB_TOKEN` do not trigger downstream push workflows.
After a dependency merge, the automation explicitly dispatches the trusted
default-branch book build and deployment so the published site stays current.
