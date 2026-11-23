#!/usr/bin/env bash
# Regular Docker host by default. For a shared Docker socket, set VNAV_HOST_HOME
# to the host path corresponding to the home directory inside this container.
set -euo pipefail
IMAGE=${1:?usage: $0 orbslam:latest|kimera:latest [cmd ...]}
shift
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
DATASETS=${VNAV_DATASET_ROOT:-$HOME/datasets/vnav}
to_host() {
  if [[ -n ${VNAV_HOST_HOME:-} && ( $1 == "$HOME" || $1 == "$HOME/"* ) ]]; then
    printf '%s%s\n' "${VNAV_HOST_HOME%/}" "${1#"$HOME"}"
  else
    printf '%s\n' "$1"
  fi
}
HOST_LAB_DIR=${VNAV_HOST_LAB_DIR:-$(to_host "$SCRIPT_DIR")}
HOST_DATASETS=${VNAV_HOST_DATASETS:-$(to_host "$DATASETS")}
[[ -d $DATASETS/MH_01_easy ]] || { echo "Dataset not found: $DATASETS/MH_01_easy" >&2; exit 1; }
export DISPLAY=${DISPLAY:-:0}
DISPLAY_NUM=$(printf '%s' "$DISPLAY" | sed -E 's/^[^:]*:([0-9]+).*/\1/')
NAME="lab9-${IMAGE%%:*}"
if [[ $(docker inspect --format '{{.State.Running}}' "$NAME" 2>/dev/null || true) == true ]]; then
  echo "Container $NAME is already running; stop it before another run." >&2
  exit 1
fi
docker rm "$NAME" >/dev/null 2>&1 || true
mkdir -p "$SCRIPT_DIR/output/orbslam" "$SCRIPT_DIR/output/kimera"
TTY=(); [[ ! -t 0 ]] || TTY=(-it)
docker run --rm "${TTY[@]}" --name "$NAME" --network "${LAB9_NET:-host}" \
  -v "/tmp/.X11-unix/X${DISPLAY_NUM}:/tmp/.X11-unix/X${DISPLAY_NUM}" \
  -v "${HOST_DATASETS}:/datasets:ro" \
  -v "${HOST_LAB_DIR}/output:/output:rw" \
  -v "${HOST_LAB_DIR}/params:/kimera_params:ro" \
  -e DISPLAY "$IMAGE" "$@"
