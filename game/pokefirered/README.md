# Pokémon FireRed — educational "Quiz Battle" mod (in progress)

This is the FireRed (Game Boy **Advance**) version of the educational mod. The
goal is the same as the Pokémon Red version in `../pokered`: battles and helpful
NPCs quietly teach grade 1–5 school material so the player learns while playing.
FireRed is chosen for its much nicer GBA-era graphics.

## Status

- [x] Toolchain proven — FireRed builds here with the modern `arm-none-eabi`
      compiler (`make modern`), producing a 16 MB `.gba` ROM.
- [x] Upstream pinned (`PINNED_COMMIT.txt`) + `setup.sh` to reproduce the tree.
- [x] Question banks ported to C (grade 1–5 content from the Red version):
      `mod/src/quiz_data.c`, `mod/include/quiz_battle.h`.
- [x] **Quiz Battle engine + attack hook** (`mod/src/quiz_battle.c`): a new
      battle-script command `showquiz` (0xF8) asks the player a badge-scaled
      question when they use a damaging move; a wrong answer makes the move
      miss. Builds cleanly into the ROM; boots in the headless emulator test.
      The UI reuses the engine's own Yes/No window + cursor (a clean 2-choice),
      so the selection always matches the highlighted answer.
- [ ] Expand the answer UI to 3–4 choices (custom battle window).
- [ ] Defense hook (wrong answer → enemy doubled crit) + item-use gate.
- [ ] Auto-heal after battle, forgiving difficulty, no overworld status.
- [x] Offline single-file player working (see `../play-gba`).

## How it's organized

To keep this repo small we do **not** commit the ~80 MB upstream source. Instead:

- `PINNED_COMMIT.txt` — the exact upstream commit we build against.
- `setup.sh` — clones that commit into `./src` and overlays our changes.
- `mod/` — **our** changed/added source files (created as the port proceeds),
  laid out with the same paths as the upstream tree.

## Build

```sh
# one-time tools (Ubuntu/Debian)
sudo apt-get install -y build-essential git libpng-dev \
     gcc-arm-none-eabi binutils-arm-none-eabi libnewlib-arm-none-eabi

cd game/pokefirered
./setup.sh
cd src && make modern -j"$(nproc)"
# output: pokefirered_modern.gba (16 MB)
```

## Playing it (offline)

The single-file `.html` model is preserved: see `../play-gba`, which bakes the
ROM + a pure-JS GBA emulator (IodineGBA) + an open-source GBA BIOS into one
self-contained file that runs offline from `file://` on Windows/Android. Build
it with `python3 ../play-gba/build_player.py`.

Because a GBA ROM is 16 MB and the core is pure JavaScript, that file is ~22 MB
and its speed depends on the device. For the smoothest experience you can also
use a native open-source emulator:

- **mGBA** — open source (MPL-2.0), Windows + Android. Load `pokefirered_modern.gba`.
