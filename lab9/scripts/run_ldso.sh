#!/usr/bin/env bash
# Deliverable 7: run LDSO (monocular, cam0 only) on the full EuRoC MH_01_easy sequence.
# Output: results/d7/results.txt (with loop closing) and results.txt.noloop (without).
#   env: NOGUI=1 (default). NOGUI=0 requires closing the viewer after completion.
set -euo pipefail
LAB=$(cd "$(dirname "$0")/.." && pwd)
LDSO=${LDSO_DIR:-$HOME/vnav-builds/ldso}
CAM0=${CAM0:-$HOME/datasets/vnav/MH_01_easy/mav0/cam0}
OUT=$LAB/results/d7
mkdir -p "$OUT"
export DISPLAY=${DISPLAY:-:0}
export LD_LIBRARY_PATH=$HOME/vnav-builds/pangolin/lib:${LD_LIBRARY_PATH:-}
cd "$LDSO"   # LDSO loads ./vocab/orbvoc.dbow3 and ./examples/EUROC/EUROC.txt relative to here
mkdir -p "$LAB/.build"
WORK=$(mktemp -d "$LAB/.build/ldso-run-XXXXXX")
trap 'rm -rf "$WORK"' EXIT
started=$(date -Is)
status=0
if ./bin/run_dso_euroc preset=0 files="$CAM0" output="$WORK/results.txt" \
    nogui="${NOGUI:-1}" >"$OUT/ldso_run.log" 2>&1; then :; else status=$?; fi
if [[ $status == 0 ]]; then
  if grep -q 'Lost!' "$OUT/ldso_run.log"; then status=1; fi
  for suffix in '' .noloop; do
    if ! python3 "$LAB/scripts/fix_ldso.py" "$WORK/results.txt$suffix" "$WORK/check$suffix.txt" \
      >>"$OUT/ldso_run.log" 2>&1; then status=1; fi
    if ! python3 "$LAB/scripts/validate_trajectory.py" "$WORK/check$suffix.txt" \
      >>"$OUT/ldso_run.log" 2>&1; then status=1; fi
  done
fi
python3 "$LAB/scripts/record_run.py" "$OUT/ldso_run.json" --system ldso \
  --started "$started" --exit-code "$status" --dataset "${CAM0%/mav0/cam0}" \
  --file "$OUT/ldso_run.log" --file "$WORK/results.txt" --file "$WORK/results.txt.noloop"
[[ $status == 0 ]] || { echo "LDSO failed; archived trajectories were not replaced." >&2; exit "$status"; }
cp "$WORK/results.txt" "$WORK/results.txt.noloop" "$OUT/"
echo "loops accepted: $(grep -c 'Loop detected' "$OUT/ldso_run.log" || true)"
echo "→ $OUT/results.txt ($(wc -l <"$OUT/results.txt") keyframe poses)"

