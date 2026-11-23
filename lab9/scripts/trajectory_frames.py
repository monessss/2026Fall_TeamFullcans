#!/usr/bin/env python3
"""Prepare D7 at cam0; T_BS maps cam0 coordinates into body coordinates.

D6 compares body/IMU poses. ORB-SLAM3's stereo-inertial EuRoC exporter and
Kimera export body poses, whereas LDSO exports camera poses. A left global
alignment cannot replace the right-multiplied sensor extrinsic.
"""
import re
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation
from evo.core.trajectory import PoseTrajectory3D
from evo.tools import file_interface


def read_extrinsic(path):
    text = Path(path).read_text()
    match = re.search(r"T_BS:\s*.*?data:\s*\[([^]]+)\]", text, re.S)
    if match is None:
        raise ValueError(f"T_BS matrix missing: {path}")
    transform = np.array([float(v) for v in match[1].split(",")]).reshape(4, 4)
    rotation = transform[:3, :3]
    if not (np.isfinite(transform).all()
            and np.allclose(transform[3], [0, 0, 0, 1])
            and np.allclose(rotation.T @ rotation, np.eye(3), atol=1e-6)
            and np.isclose(np.linalg.det(rotation), 1, atol=1e-6)):
        raise ValueError(f"Invalid rigid extrinsic: {path}")
    return transform


def body_to_camera(trajectory, transform):
    """T_WC = T_WB T_BC; preserve timestamps and return a new trajectory."""
    body_rotation = Rotation.from_quat(
        trajectory.orientations_quat_wxyz[:, [1, 2, 3, 0]]).as_matrix()
    positions = trajectory.positions_xyz + np.einsum(
        "nij,j->ni", body_rotation, transform[:3, 3])
    camera_rotation = body_rotation @ transform[:3, :3]
    quaternions = Rotation.from_matrix(camera_rotation).as_quat()[:, [3, 0, 1, 2]]
    return PoseTrajectory3D(positions_xyz=positions,
                           orientations_quat_wxyz=quaternions,
                           timestamps=trajectory.timestamps.copy())


def prepare_d7(lab):
    lab = Path(lab)
    transform = read_extrinsic(lab / "params/LeftCameraParams.yaml")
    sources = {
        "data_cam0.tum": "data.tum",
        "kimera_cam0.txt": "kimera/kimera.txt",
        "orb_slam3_cam0.txt": "orbslam/orb_slam3.txt",
    }
    output = lab / ".build/d7_frames"
    output.mkdir(parents=True, exist_ok=True)
    for target, source in sources.items():
        trajectory = file_interface.read_tum_trajectory_file(
            str(lab / "results/d6" / source))
        file_interface.write_tum_trajectory_file(
            str(output / target), body_to_camera(trajectory, transform))
    return transform


if __name__ == "__main__":
    transform = prepare_d7(Path(__file__).resolve().parents[1])
    print(f"D7 reference point: cam0; body-camera offset {np.linalg.norm(transform[:3, 3]):.9f} m")
