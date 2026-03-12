#!/usr/bin/env bash
set -euo pipefail

find_juliaup_binary() {
  local requested_version="${1:-}"
  local juliaup_root="${HOME}/.julia/juliaup"
  local matches

  if [[ ! -d "$juliaup_root" ]]; then
    if [[ -n "$requested_version" ]]; then
      printf 'Could not find a Julia %s binary under %s. Install it with `juliaup add %s` or set JULIA_BIN explicitly.\n' \
        "$requested_version" "$juliaup_root" "$requested_version" >&2
    fi
    return 1
  fi

  if [[ -n "$requested_version" ]]; then
    matches="$(
      find "$juliaup_root" -maxdepth 3 -type f -path "*/bin/julia" \
        | grep -E "/julia-${requested_version//./\\.}(\\.[0-9]+)?\\+.*?/bin/julia$" \
        | sort -V || true
    )"
    if [[ -n "$matches" ]]; then
      printf '%s\n' "$matches" | tail -n 1
      return 0
    fi

    printf 'Could not find a Julia %s binary under %s. Install it with `juliaup add %s` or set JULIA_BIN explicitly.\n' \
      "$requested_version" "$juliaup_root" "$requested_version" >&2
    return 1
  fi

  matches="$(
    find "$juliaup_root" -maxdepth 3 -type f -path '*/bin/julia' | sort -V || true
  )"
  if [[ -n "$matches" ]]; then
    printf '%s\n' "$matches" | tail -n 1
    return 0
  fi

  return 1
}

if [[ -n "${JULIA_BIN:-}" ]]; then
  printf '%s\n' "$JULIA_BIN"
  exit 0
fi

if [[ -n "${JULIA_VERSION:-}" ]]; then
  find_juliaup_binary "$JULIA_VERSION"
  exit 0
fi

if command -v julia >/dev/null 2>&1; then
  candidate="$(command -v julia)"
else
  printf 'Could not find a `julia` executable on your PATH. Install Julia or set JULIA_BIN or JULIA_VERSION.\n' >&2
  exit 1
fi

resolved="$(readlink -f "$candidate" 2>/dev/null || printf '%s\n' "$candidate")"

if [[ "$(basename "$resolved")" == "julialauncher" ]]; then
  if latest_binary="$(find_juliaup_binary)"; then
    printf '%s\n' "$latest_binary"
    exit 0
  fi
fi

printf '%s\n' "$candidate"
