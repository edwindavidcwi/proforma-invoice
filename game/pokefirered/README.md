# Pokémon FireRed — educational "Quiz Battle" mod (in progress)

This is the FireRed (Game Boy **Advance**) version of the educational mod. The
goal is the same as the Pokémon Red version in `../pokered`: battles and helpful
NPCs quietly teach grade 1–5 school material so the player learns while playing.
FireRed is chosen for its much nicer GBA-era graphics.

## Status

- [x] Toolchain proven — FireRed builds here with the modern `arm-none-eabi`
      compiler (`make modern`), producing a 16 MB `.gba` ROM.
- [x] Upstream pinned (`PINNED_COMMIT.txt`) + `setup.sh` to reproduce the tree.
- [ ] Quiz Battle engine ported to FireRed's C battle code (the big task —
      FireRed is written in C, so the Red assembly hooks are reimplemented, not
      copied).
- [ ] Question banks (reuse the grade 1–5 content from the Red version).
- [ ] Auto-heal after battle, forgiving difficulty, no-status, etc.
- [ ] Offline player decision (see below).

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

A GBA ROM is 16 MB, and the good open-source in-browser GBA core (mGBA-wasm)
needs multi-threading / cross-origin isolation, which a plain local `file://`
page can't provide. So the single-file `.html` trick used for the tiny GBC ROM
does not transfer cleanly to GBA. The recommended offline path is a native
open-source emulator:

- **mGBA** — open source (MPL-2.0), Windows + Android. Load `pokefirered_modern.gba`.

(A pure-JS in-browser single-file player using IodineGBA is possible as a
convenience but is larger and slower; see the project notes / ask if you want it.)
