#!/usr/bin/env bash
set -euo pipefail

candidate="${JULIA_BIN:-$(command -v julia)}"
resolved="$(readlink -f "$candidate" 2>/dev/null || printf '%s\n' "$candidate")"

if [[ "$(basename "$resolved")" == "julialauncher" ]]; then
  juliaup_root="${HOME}/.julia/juliaup"
  if [[ -d "$juliaup_root" ]]; then
    latest_binary="$(
      find "$juliaup_root" -maxdepth 3 -type f -path '*/bin/julia' | sort | tail -n 1
    )"
    if [[ -n "$latest_binary" ]]; then
      printf '%s\n' "$latest_binary"
      exit 0
    fi
  fi
fi

printf '%s\n' "$candidate"
