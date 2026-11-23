#!/usr/bin/env bash
# --results evaluates the committed raw trajectories, without Docker or images.
set -euo pipefail
LAB=$(cd "$(dirname "$0")/.." && pwd)
cd "$LAB"
OUT=results/d6
case ${1:-} in
  --results) SOURCE=$OUT ;;
  '') SOURCE=output ;;
  *) echo "usage: $0 [--results]" >&2; exit 2 ;;
esac
export MPLBACKEND=Agg
python3 scripts/validate_trajectory.py "$SOURCE/orbslam/CameraTrajectory.txt"
python3 scripts/validate_trajectory.py "$SOURCE/kimera/traj_vio.csv"
python3 fix_timestamps.py --root "$SOURCE"
if [[ $SOURCE != "$OUT" ]]; then
  mkdir -p "$OUT/orbslam" "$OUT/kimera"
  cp "$SOURCE/orbslam/orb_slam3.txt" "$OUT/orbslam/"
  cp "$SOURCE/kimera/kimera.txt" "$OUT/kimera/"
  GT_CSV=${GT_CSV:-${VNAV_DATASET_ROOT:-$HOME/datasets/vnav}/MH_01_easy/mav0/state_groundtruth_estimate0/data.csv}
  python3 - "$GT_CSV" "$OUT/data.tum" <<'PY'
import sys
from pathlib import Path
from evo.tools import file_interface as fi
source, target = sys.argv[1], Path(sys.argv[2])
trajectory = fi.read_euroc_csv_trajectory(source)
temporary = target.with_suffix('.tum.tmp')
fi.write_tum_trajectory_file(str(temporary), trajectory)
temporary.replace(target)
PY
fi
python3 scripts/validate_trajectory.py "$OUT/data.tum"
K=$OUT/kimera/kimera.txt
O=$OUT/orbslam/orb_slam3.txt
rm -rf "$OUT/evo"
mkdir -p "$OUT/evo"
evo_traj tum "$K" "$O" --plot_mode xyz --save_plot "$OUT/evo/traj_unaligned.png" \
  | tee "$OUT/evo/traj_unaligned.txt"
evo_traj tum "$K" "$O" --ref "$OUT/data.tum" --align --plot_mode xyz \
  --save_plot "$OUT/evo/traj_aligned.png" | tee "$OUT/evo/traj_aligned.txt"
for name in kimera orb_slam3; do
  f=$O; [[ $name != kimera ]] || f=$K
  evo_ape tum "$OUT/data.tum" "$f" --align -va \
    --save_results "$OUT/evo/ape_${name}.zip" | tee "$OUT/evo/ape_${name}.txt"
  evo_ape tum "$OUT/data.tum" "$f" --align --correct_scale -va \
    --save_results "$OUT/evo/ape_${name}_sim3.zip" | tee "$OUT/evo/ape_${name}_sim3.txt"
done
