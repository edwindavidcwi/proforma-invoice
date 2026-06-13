#!/usr/bin/env bash
# Build the single-file player and copy it into the app's assets so the APK
# bundles the game. Run this before building the APK.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"

# 1) (Re)build the offline player HTML from the current ROM.
( cd "$HERE/../play" && python3 build_player.py --out "$HERE/app/src/main/assets/PokemonQuiz.html" )

echo "==> Bundled $(du -h "$HERE/app/src/main/assets/PokemonQuiz.html" | cut -f1) into assets."
echo "==> Now build the APK:"
echo "      cd \"$HERE\" && ./gradlew assembleRelease"
echo "    APK output: app/build/outputs/apk/release/app-release.apk"
