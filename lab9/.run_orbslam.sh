#!/usr/bin/env bash
set -euo pipefail
ORB=${ORB_SLAM3_ROOT:-/workspace/ORB_SLAM3}
OUT=${ORB_OUTPUT_DIR:-/output/orbslam}
DATASET=${ORB_DATASET:-/datasets/MH_01_easy}
mkdir -p "$OUT"
rm -f "$OUT/CameraTrajectory.txt"
RUN_DIR=$(mktemp -d)
trap 'rm -rf "$RUN_DIR"' EXIT
cd "$RUN_DIR"
"$ORB/Examples/Stereo-Inertial/stereo_inertial_euroc" \
  "$ORB/Vocabulary/ORBvoc.txt" "$ORB/Examples/Stereo-Inertial/EuRoC.yaml" \
  "$DATASET" "$ORB/Examples/Stereo-Inertial/EuRoC_TimeStamps/MH01.txt"
test -s CameraTrajectory.txt
cp CameraTrajectory.txt "$OUT/CameraTrajectory.txt.tmp"
mv "$OUT/CameraTrajectory.txt.tmp" "$OUT/CameraTrajectory.txt"

