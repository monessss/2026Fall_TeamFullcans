"""Checks for sensor-frame evaluation and stale-output failure regressions."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import numpy as np
from scipy.spatial.transform import Rotation
from evo.core.trajectory import PoseTrajectory3D

LAB = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(LAB / 'scripts'))
from trajectory_frames import body_to_camera, read_extrinsic
from validate_trajectory import validate


class FrameConversionTests(unittest.TestCase):
    def test_rotating_body_requires_rotating_camera_lever_arm(self):
        rotations = Rotation.from_euler('z', np.array([[0], [90], [180]]), degrees=True)
        body = PoseTrajectory3D(positions_xyz=np.zeros((3, 3)),
            orientations_quat_wxyz=rotations.as_quat()[:, [3, 0, 1, 2]],
            timestamps=np.array([10., 11., 12.]))
        transform = np.eye(4)
        transform[:3, 3] = [1, 0, 0]
        transform[:3, :3] = Rotation.from_euler('x', 30, degrees=True).as_matrix()
        camera = body_to_camera(body, transform)
        np.testing.assert_allclose(camera.positions_xyz, [[1, 0, 0], [0, 1, 0], [-1, 0, 0]], atol=1e-12)
        camera_rotations = Rotation.from_quat(camera.orientations_quat_wxyz[:, [1, 2, 3, 0]]).as_matrix()
        np.testing.assert_allclose(camera_rotations, rotations.as_matrix() @ transform[:3, :3], atol=1e-12)
        np.testing.assert_array_equal(camera.timestamps, body.timestamps)
        np.testing.assert_array_equal(body.positions_xyz, np.zeros((3, 3)))

    def test_supplied_calibration_has_expected_offset(self):
        transform = read_extrinsic(LAB / 'params/LeftCameraParams.yaml')
        self.assertAlmostEqual(np.linalg.norm(transform[:3, 3]), .06890325790004832)

    def test_rejects_nonrigid_extrinsic(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'bad.yaml'
            path.write_text('T_BS:\n data: [2,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1]')
            with self.assertRaises(ValueError):
                read_extrinsic(path)


class OrbLauncherTests(unittest.TestCase):
    def launch(self, program):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            binary = root / 'orb/Examples/Stereo-Inertial/stereo_inertial_euroc'
            binary.parent.mkdir(parents=True)
            binary.write_text('#!/bin/sh\n' + program)
            binary.chmod(0o755)
            output = root / 'output'
            output.mkdir()
            (output / 'CameraTrajectory.txt').write_text('OLD_TRAJECTORY\n')
            env = {**os.environ, 'ORB_SLAM3_ROOT': str(root / 'orb'), 'ORB_OUTPUT_DIR': str(output)}
            completed = subprocess.run(['bash', str(LAB / '.run_orbslam.sh')], env=env, capture_output=True)
            path = output / 'CameraTrajectory.txt'
            return completed.returncode, path.read_text() if path.exists() else None

    def test_nonzero_exit_does_not_reuse_previous_output(self):
        code, data = self.launch('exit 42\n')
        self.assertEqual(code, 42)
        self.assertIsNone(data)

    def test_success_without_new_output_is_failure(self):
        code, data = self.launch('exit 0\n')
        self.assertNotEqual(code, 0)
        self.assertIsNone(data)

    def test_success_exports_only_new_output(self):
        code, data = self.launch("printf 'NEW_TRAJECTORY\\n' > CameraTrajectory.txt\n")
        self.assertEqual(code, 0)
        self.assertEqual(data, 'NEW_TRAJECTORY\n')


class LdsoLauncherTests(unittest.TestCase):
    def test_nonzero_exit_retains_archive_and_records_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            lab = root / 'lab'
            scripts = lab / 'scripts'
            scripts.mkdir(parents=True)
            for name in ['run_ldso.sh', 'record_run.py']:
                (scripts / name).write_bytes((LAB / 'scripts' / name).read_bytes())
            binary = root / 'ldso/bin/run_dso_euroc'
            binary.parent.mkdir(parents=True)
            binary.write_text('#!/bin/sh\nexit 42\n')
            binary.chmod(0o755)
            archive = lab / 'results/d7'
            archive.mkdir(parents=True)
            (archive / 'results.txt').write_text('OLD_ARCHIVE\n')
            env = {**os.environ, 'LDSO_DIR': str(root / 'ldso'), 'CAM0': str(root / 'dataset/mav0/cam0')}
            completed = subprocess.run(['bash', str(scripts / 'run_ldso.sh')], env=env, capture_output=True)
            self.assertEqual(completed.returncode, 42)
            self.assertEqual((archive / 'results.txt').read_text(), 'OLD_ARCHIVE\n')
            summary = json.loads((archive / 'ldso_run.json').read_text())
            self.assertEqual(summary['status'], 'failed')
            self.assertEqual(summary['exit_code'], 42)


class ValidationTests(unittest.TestCase):
    def test_nonfinite_and_duplicate_stamps_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'trajectory.txt'
            for text in ['0 0 0 0 0 0 0 1\n0 1 0 0 0 0 0 1\n',
                         '0 0 0 0 0 0 0 1\n1 nan 0 0 0 0 0 1\n']:
                path.write_text(text)
                with self.assertRaises(ValueError):
                    validate(path)


class DockerPathTests(unittest.TestCase):
    def test_default_network_and_dataset_mount_are_portable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'dataset/MH_01_easy').mkdir(parents=True)
            stub = root / 'docker'
            stub.write_text('#!/usr/bin/env python3\nimport os,sys,json\n'
                'if sys.argv[1] == "inspect": print("false")\n'
                'if sys.argv[1] == "run": open(os.environ["DOCKER_ARGS"], "w").write(json.dumps(sys.argv[1:]))\n')
            stub.chmod(0o755)
            env = {k: v for k, v in os.environ.items() if not k.startswith(('VNAV_', 'LAB9_NET'))}
            env.update(PATH=str(root) + os.pathsep + env['PATH'], VNAV_DATASET_ROOT=str(root / 'dataset'),
                       DOCKER_ARGS=str(root / 'arguments.json'))
            completed = subprocess.run(['bash', str(LAB / 'run_docker_vnav.sh'), 'orbslam:latest'], env=env, capture_output=True)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            arguments = json.loads((root / 'arguments.json').read_text())
            self.assertEqual(arguments[arguments.index('--network') + 1], 'host')
            self.assertIn(str(root / 'dataset') + ':/datasets:ro', arguments)
            self.assertNotIn('/srv/vnav2023/homes/xby', ' '.join(arguments))


if __name__ == '__main__':
    unittest.main()
