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
        | grep -E "/julia-${requested_version//./\\.}(\\.[0-9]+)?\\+[^/]*/bin/julia$" \
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

candidate_matches_version() {
  local candidate="$1"
  local requested_version="$2"
  local version_output
  local actual_version

  version_output="$(("$candidate" --version 2>/dev/null || true) | head -n 1)"
  if [[ ! "$version_output" =~ julia[[:space:]]+version[[:space:]]+([0-9]+\.[0-9]+(\.[0-9]+)?) ]]; then
    return 1
  fi

  actual_version="${BASH_REMATCH[1]}"
  [[ "$actual_version" == "$requested_version" || "$actual_version" == "$requested_version".* ]]
}

if [[ -n "${JULIA_BIN:-}" ]]; then
  printf '%s\n' "$JULIA_BIN"
  exit 0
fi

if command -v julia >/dev/null 2>&1; then
  candidate="$(command -v julia)"
else
  candidate=""
fi

resolved="$(readlink -f "$candidate" 2>/dev/null || printf '%s\n' "$candidate")"

if [[ -n "${JULIA_VERSION:-}" ]]; then
  if [[ "$(basename "$resolved")" == "julialauncher" ]]; then
    if versioned_binary="$(find_juliaup_binary "$JULIA_VERSION")"; then
      printf '%s\n' "$versioned_binary"
      exit 0
    fi
  fi

  if [[ -n "$candidate" ]] && candidate_matches_version "$candidate" "$JULIA_VERSION"; then
    printf '%s\n' "$candidate"
    exit 0
  fi

  if [[ -n "$candidate" ]]; then
    printf 'Could not find a Julia %s binary. The PATH `julia` does not match the requested version and no juliaup install was found. Set JULIA_BIN explicitly to continue.\n' \
      "$JULIA_VERSION" >&2
  else
    printf 'Could not find a Julia %s binary. Install it with `juliaup add %s`, put a matching `julia` on PATH, or set JULIA_BIN explicitly.\n' \
      "$JULIA_VERSION" "$JULIA_VERSION" >&2
  fi
  exit 1
fi

if [[ -z "$candidate" ]]; then
  printf 'Could not find a `julia` executable on your PATH. Install Julia or set JULIA_BIN or JULIA_VERSION.\n' >&2
  exit 1
fi

if [[ "$(basename "$resolved")" == "julialauncher" ]]; then
  if latest_binary="$(find_juliaup_binary)"; then
    printf '%s\n' "$latest_binary"
    exit 0
  fi
fi

printf '%s\n' "$candidate"
