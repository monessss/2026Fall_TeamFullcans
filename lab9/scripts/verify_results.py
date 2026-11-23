#!/usr/bin/env python3
"""Independent SVD/nearest-time verification of archived trajectory metrics.

This evaluates existing outputs. It does not certify how many image frames were
processed, how many loop events were accepted, or whether a fresh SLAM run works.
"""
import hashlib
import json
from importlib.metadata import version
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation

LAB = Path(__file__).resolve().parents[1]


def associate(reference, estimate, max_difference=.01):
    times = reference[:, 0]
    right = np.searchsorted(times, estimate[:, 0]).clip(0, len(times) - 1)
    left = (right - 1).clip(0)
    indices = np.where(abs(times[left] - estimate[:, 0]) <= abs(times[right] - estimate[:, 0]), left, right)
    keep = abs(times[indices] - estimate[:, 0]) <= max_difference
    return reference[indices[keep]], estimate[keep]


def svd_metrics(reference, estimate):
    ref, est = associate(reference, estimate)
    x = est[:, 1:4] - est[:, 1:4].mean(0)
    y = ref[:, 1:4] - ref[:, 1:4].mean(0)
    u, singular, vt = np.linalg.svd(y.T @ x / len(x))
    correction = np.eye(3)
    correction[-1, -1] = np.linalg.det(u @ vt)
    rotation = u @ correction @ vt
    scale = np.trace(np.diag(singular) @ correction) / np.mean(np.sum(x*x, axis=1))
    rmse = lambda residual: float(np.sqrt(np.mean(np.sum(residual**2, axis=1))))
    return {'matched_poses': len(x), 'se3_rmse': rmse(x @ rotation.T - y),
            'sim3_rmse': rmse(scale * x @ rotation.T - y), 'sim3_scale': float(scale)}


def main():
    from trajectory_frames import prepare_d7, read_extrinsic
    prepare_d7(LAB)
    results = LAB / 'results'
    checks = {}
    for part, reference, systems in [
        ('d6', 'data.tum', {'Kimera-VIO': 'kimera/kimera.txt', 'ORB-SLAM3': 'orbslam/orb_slam3.txt'}),
        ('d7', 'data_cam0.tum', {'Kimera-VIO': 'kimera_cam0.txt', 'ORB-SLAM3': 'orb_slam3_cam0.txt',
                              'LDSO': 'ldso.txt', 'LDSO (no loop closure)': 'ldso_noloop.txt'}),
    ]:
        root = results / part
        frames = LAB / '.build/d7_frames' if part == 'd7' else root
        reference_data = np.loadtxt(frames / reference)
        recorded = json.loads((root / 'metrics.json').read_text())
        checks[part] = {}
        for name, relative in systems.items():
            source = frames / relative if part == 'd7' and 'cam0' in relative else root / relative
            estimate = np.loadtxt(source)
            values = svd_metrics(reference_data, estimate)
            entry = recorded[name]
            expected = {'matched_poses': entry['matched_poses'], 'sim3_scale': entry['sim3_scale'],
                        'se3_rmse': entry['ate_se3']['rmse'] if part == 'd6' else entry['ate_se3_rmse'],
                        'sim3_rmse': entry['ate_sim3_rmse'] if part == 'd6' else entry['ate_sim3']['rmse']}
            for key, value in expected.items():
                if not np.isclose(values[key], value, rtol=1e-10, atol=1e-10):
                    raise AssertionError(f'{part}/{name}/{key}: {values[key]} != {value}')
            checks[part][name] = values
    raw = np.loadtxt(results / 'd6/orbslam/CameraTrajectory.txt')
    raw[:, 0] /= 1e9
    np.testing.assert_array_equal(raw, np.loadtxt(results / 'd6/orbslam/orb_slam3.txt'))
    raw = np.loadtxt(results / 'd6/kimera/traj_vio.csv', delimiter=',')
    expected = np.column_stack([raw[:, 0]/1e9, raw[:, 1:4], raw[:, 5:8], raw[:, 4]])
    np.testing.assert_array_equal(expected, np.loadtxt(results / 'd6/kimera/kimera.txt'))
    # A common D6 time grid checks whether keyframe sampling changes the ranking.
    kimera = np.loadtxt(results / 'd6/kimera/kimera.txt')
    orb = np.loadtxt(results / 'd6/orbslam/orb_slam3.txt')
    truth = np.loadtxt(results / 'd6/data.tum')
    kimera = kimera[(kimera[:, 0] >= truth[0, 0]) & (kimera[:, 0] <= truth[-1, 0])]
    def interpolate_positions(data):
        return np.column_stack([kimera[:, 0]] + [np.interp(kimera[:, 0], data[:, 0], data[:, i]) for i in range(1, 4)])
    checks['common_d6_time_grid'] = {name: svd_metrics(interpolate_positions(truth), data)
        for name, data in [('Kimera-VIO', kimera), ('ORB-SLAM3', interpolate_positions(orb))]}
    # Verify camera reference positions independently of trajectory_frames.py.
    transform = read_extrinsic(LAB / 'params/LeftCameraParams.yaml')
    rotation = Rotation.from_quat(truth[:, [4, 5, 6, 7]]).as_matrix()
    expected_camera = truth[:, 1:4] + np.einsum('nij,j->ni', rotation, transform[:3, 3])
    np.testing.assert_allclose(expected_camera, np.loadtxt(LAB / '.build/d7_frames/data_cam0.tum')[:, 1:4], atol=1e-12)
    checks['conversion_checks'] = 'passed'
    files = [p for p in results.rglob('*') if p.is_file() and p.suffix in {'.txt', '.csv', '.tum', '.json'}
             and p.name != 'validation_summary.json']
    summary = {'scope': 're-evaluation of archived trajectories; no new SLAM run',
               'versions': {name: version(name) for name in ['numpy', 'scipy', 'evo', 'matplotlib']},
               'checks': checks,
               'sha256': {str(p.relative_to(LAB)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)},
               'historical_runtime_logs_available': False}
    (results / 'validation_summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(checks, indent=2))


if __name__ == '__main__':
    main()
