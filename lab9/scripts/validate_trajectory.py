#!/usr/bin/env python3
"""Reject empty, malformed, non-finite or non-monotonic SLAM output files."""
import argparse
from pathlib import Path

import numpy as np


def validate(path):
    path = Path(path)
    rows = np.loadtxt(path, delimiter="," if path.suffix == ".csv" else None,
                      comments="#", ndmin=2)
    if rows.shape[0] < 2 or rows.shape[1] < 8 or not np.isfinite(rows).all():
        raise ValueError(f"Invalid trajectory: {path}")
    if not (np.diff(rows[:, 0]) > 0).all():
        raise ValueError(f"Non-increasing timestamps: {path}")
    return {"poses": len(rows), "first_timestamp_raw": float(rows[0, 0]),
            "last_timestamp_raw": float(rows[-1, 0])}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path")
    args = parser.parse_args()
    print(validate(args.path))
