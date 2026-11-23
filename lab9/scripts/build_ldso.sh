#!/usr/bin/env bash
# Deliverable 7: build LDSO (https://github.com/tum-vision/LDSO) outside the repo, in
# ~/vnav-builds. LDSO needs Pangolin, which this container does not have, so Pangolin v0.6
# (the version used in the ORB-SLAM3 image) is installed into a local prefix.
set -euo pipefail
B=${LDSO_BUILD_ROOT:-$HOME/vnav-builds}
J=${JOBS:-10}
mkdir -p "$B"

if [[ ! -f $B/pangolin/lib/libpangolin.so ]]; then
  [[ -d $B/pangolin-src ]] || git clone --depth 1 --branch v0.6 \
      https://github.com/stevenlovegrove/Pangolin.git "$B/pangolin-src"
  cmake -S "$B/pangolin-src" -B "$B/pangolin-src/build" -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_INSTALL_PREFIX="$B/pangolin" -DBUILD_EXAMPLES=OFF -DBUILD_TESTS=OFF \
      -DBUILD_PANGOLIN_PYTHON=OFF -DBUILD_PANGOLIN_FFMPEG=OFF
  cmake --build "$B/pangolin-src/build" -j"$J" --target install
fi

LDSO_REV=9b0c48cfd3b3ee95a8dbf1aef2371ed4fca6f81a
[[ -d $B/ldso ]] || git clone https://github.com/tum-vision/LDSO.git "$B/ldso"
cd "$B/ldso"
[[ -z $(git status --porcelain) ]] || { echo "LDSO source has local changes; refusing checkout." >&2; exit 1; }
git cat-file -e "$LDSO_REV^{commit}" 2>/dev/null || git fetch origin "$LDSO_REV"
git checkout --detach "$LDSO_REV"
for d in thirdparty/DBoW3 thirdparty/g2o; do
  cmake -S "$d" -B "$d/build" -DCMAKE_BUILD_TYPE=Release
  cmake --build "$d/build" -j"$J"
done
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release \
    -DPangolin_DIR="$B/pangolin/lib/cmake/Pangolin"
cmake --build build -j"$J"
echo "→ $B/ldso/bin/run_dso_euroc"

