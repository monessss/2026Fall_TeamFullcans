#!/usr/bin/env python3
"""Record a new run's status and output hashes; never reconstruct historical logs."""
import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("output")
parser.add_argument("--system", required=True)
parser.add_argument("--started", required=True)
parser.add_argument("--exit-code", type=int, required=True)
parser.add_argument("--dataset", required=True)
parser.add_argument("--file", action="append", default=[])
args = parser.parse_args()
dataset = Path(args.dataset)
index = dataset / "mav0/cam0/data.csv"
inputs = None
if index.exists():
    inputs = sum(bool(line.strip()) and not line.startswith("#") for line in index.read_text().splitlines())
try:
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True,
        cwd=Path(__file__).resolve().parents[1], stderr=subprocess.DEVNULL).strip()
except subprocess.CalledProcessError:
    revision = None
files = {}
for value in args.file:
    path = Path(value)
    if path.is_file():
        files[value] = {"bytes": path.stat().st_size,
                        "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
summary = {"system": args.system, "started": args.started,
           "finished": datetime.now(timezone.utc).isoformat(),
           "exit_code": args.exit_code, "status": "success" if args.exit_code == 0 else "failed",
           "dataset": str(dataset), "input_stereo_pairs": inputs,
           "repository_commit": revision, "files": files}
path = Path(args.output)
temporary = path.with_suffix(path.suffix + ".tmp")
temporary.write_text(json.dumps(summary, indent=2) + "\n")
temporary.replace(path)
