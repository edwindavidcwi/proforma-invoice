#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Set up a buildable Pokémon FireRed tree for the educational Quiz Battle mod.
#
# Why a script instead of a vendored copy: the FireRed disassembly source tree
# is ~80 MB. Rather than commit all of upstream into this repo, we pin the exact
# upstream commit and overlay only OUR changes (the files under ./mod). This
# keeps the repo small and the build reproducible.
#
# Usage:
#   cd game/pokefirered
#   ./setup.sh           # clone pinned upstream into ./src and overlay the mod
#   cd src && make modern -j"$(nproc)"
#
# Requirements (Ubuntu/Debian):
#   sudo apt-get install -y build-essential git libpng-dev \
#        gcc-arm-none-eabi binutils-arm-none-eabi libnewlib-arm-none-eabi
# ---------------------------------------------------------------------------
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$HERE/src"
REPO="https://github.com/pret/pokefirered.git"
COMMIT="$(sed -n '2p' "$HERE/PINNED_COMMIT.txt")"

echo "==> Pinned upstream commit: $COMMIT"

if [ ! -d "$SRC/.git" ]; then
  echo "==> Cloning pokefirered into $SRC"
  git clone "$REPO" "$SRC"
fi

echo "==> Checking out pinned commit"
git -C "$SRC" fetch --depth 1 origin "$COMMIT" 2>/dev/null || git -C "$SRC" fetch origin
git -C "$SRC" checkout -q "$COMMIT"
git -C "$SRC" clean -fdq
git -C "$SRC" checkout -q .

if [ -d "$HERE/mod" ]; then
  echo "==> Overlaying mod files from ./mod"
  # Copy every file under mod/ into the source tree, preserving paths.
  ( cd "$HERE/mod" && find . -type f -print0 | while IFS= read -r -d '' f; do
      mkdir -p "$SRC/$(dirname "$f")"
      cp "$f" "$SRC/$f"
      echo "    + $f"
  done )
fi

echo "==> Done. Build with:"
echo "      cd \"$SRC\" && make modern -j\"\$(nproc)\""
