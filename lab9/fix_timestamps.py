"""Convert ORB nanoseconds to seconds and Kimera CSV to TUM; keep raw inputs."""
import argparse
from pathlib import Path
from evo.tools import file_interface

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--root', type=Path, default=Path('output'))
args = parser.parse_args()
traj = file_interface.read_tum_trajectory_file(str(args.root / 'orbslam/CameraTrajectory.txt'))
traj.timestamps = traj.timestamps / 1e9
file_interface.write_tum_trajectory_file(str(args.root / 'orbslam/orb_slam3.txt'), traj)
kimera_traj = file_interface.read_euroc_csv_trajectory(str(args.root / 'kimera/traj_vio.csv'))
file_interface.write_tum_trajectory_file(str(args.root / 'kimera/kimera.txt'), kimera_traj)
