#!/usr/bin/env bash
# Run ORB-SLAM3 and then Kimera-VIO on the full EuRoC MH_01_easy sequence (never in parallel:
# the machine has 15 GB RAM), then copy the raw trajectories into results/d6/.
#   usage: scripts/run_slam.sh [orbslam|kimera|both]   (default: both)
set -euo pipefail
LAB=$(cd "$(dirname "$0")/.." && pwd)
cd "$LAB"
OUT=results/d6
mkdir -p "$OUT"
which=${1:-both}
[[ $which == orbslam || $which == kimera || $which == both ]] || {
  echo "usage: $0 [orbslam|kimera|both]" >&2; exit 2;
}

DS=${VNAV_DATASET_ROOT:-$HOME/datasets/vnav}
# Kimera reads state_groundtruth_estimate0/sensor.yaml with cv::FileStorage, which needs a
# "%YAML:1.0" first line that the EuRoC files lack ("Cannot open file ... sensor.yaml").
# Build a hard-linked copy (no extra disk space) where only the yaml files get the header,
# so the original dataset stays untouched.
prepare_kimera_dataset() {
  local dst=$DS/MH_01_easy_kimera
  [[ -f $dst/mav0/state_groundtruth_estimate0/sensor.yaml ]] && \
    head -1 "$dst/mav0/state_groundtruth_estimate0/sensor.yaml" | grep -q '^%YAML' && return
  rm -rf "$dst"
  cp -al "$DS/MH_01_easy" "$dst"
  for f in "$dst"/mav0/*/sensor.yaml "$dst"/mav0/body.yaml; do
    { echo '%YAML:1.0'; cat "$f"; } >"$f.tmp" && rm "$f" && mv "$f.tmp" "$f"
  done
}

run() {  # $1 = orbslam|kimera
  local name=$1 started status raw
  started=$(date -Is)
  echo "== $name: started $started" | tee "$OUT/${name}_run.log"
  docker image inspect "${name}:latest" >>"$OUT/${name}_run.log"
  mkdir -p "output/$name"
  raw="output/$name/CameraTrajectory.txt"
  [[ $name != kimera ]] || raw="output/kimera/traj_vio.csv"
  rm -f "$raw"
  if [[ $1 == kimera ]]; then
    prepare_kimera_dataset
    if ./run_docker_vnav.sh kimera:latest bash run_kimera.sh -p /datasets/MH_01_easy_kimera \
      >>"$OUT/${name}_run.log" 2>&1; then status=0; else status=$?; fi
  else
    if ./run_docker_vnav.sh "$name:latest" >>"$OUT/${name}_run.log" 2>&1; then status=0; else status=$?; fi
  fi
  if [[ $status == 0 ]]; then
    python3 scripts/validate_trajectory.py "$raw" >>"$OUT/${name}_run.log" 2>&1 || status=$?
  fi
  echo "== $name: finished $(date -Is), exit $status" | tee -a "$OUT/${name}_run.log"
  python3 scripts/record_run.py "$OUT/${name}_run.json" --system "$name" \
    --started "$started" --exit-code "$status" --dataset "$DS/MH_01_easy" \
    --file "$raw" --file "$OUT/${name}_run.log"
  [[ $status == 0 ]] || { echo "$name failed (exit $status); archived trajectories were not replaced." >&2; exit "$status"; }
}

if [[ $which == orbslam || $which == both ]]; then
  run orbslam
  mkdir -p "$OUT/orbslam" && cp output/orbslam/CameraTrajectory.txt "$OUT/orbslam/"
fi
if [[ $which == kimera || $which == both ]]; then
  run kimera
  mkdir -p "$OUT/kimera" && cp output/kimera/traj_vio.csv output/kimera/StatisticsVIO.csv "$OUT/kimera/"
fi

