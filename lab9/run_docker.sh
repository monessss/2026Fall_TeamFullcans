#!/usr/bin/env bash
# Compatibility entry point for the handout.
set -euo pipefail
exec "$(dirname "$0")/run_docker_vnav.sh" "$@"
