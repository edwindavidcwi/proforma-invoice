# Offline single-file player for the FireRed (GBA) game

Builds **one self-contained `.html`** that plays a Game Boy Advance ROM in any
modern browser, **fully offline**. The emulator (pure JavaScript), an
open-source GBA BIOS, and the ROM are all inlined — nothing is downloaded at
run time, so the same single file can be shared with students and opened on
Windows or Android.

Because a GBA ROM is large (FireRed is 16 MB), the output file is **~22 MB**,
and the emulator core is pure JavaScript, so **speed depends on the device**
(fine on a modern phone/PC; slower on low-end hardware). This is the trade-off
for keeping it a single offline file — see `../pokefirered/README.md`.

## Build

```sh
# 1) build the ROM first (see ../pokefirered/README.md)
cd game/pokefirered && ./setup.sh && cd src && make modern -j"$(nproc)"

# 2) bake it into one .html
cd ../../play-gba
python3 build_player.py --rom ../pokefirered/src/pokefirered_modern.gba
# -> FireRedQuiz.html  (~22 MB)
```

The generated `.html` is intentionally **not committed** (it is large and
regenerated from the ROM). The build inputs (emulator + BIOS + driver) are
committed so anyone can reproduce it.

## How to play

- **Windows/Mac/Linux:** double-click the `.html`; it opens in your browser.
- **Android:** open it in **Firefox** (Chrome blocks local `file://` pages).
  Touch controls (D-pad, A/B, L/R, Start/Select) appear automatically.
- **Keyboard:** Arrows = move · `X` = A · `Z` = B · `A`/`S` = L/R ·
  `Enter` = Start · `Shift` = Select.
- The **Open ROM** button (or drag-and-drop) loads any other `.gba` at runtime.

## What's inside / licensing

All MIT-licensed and redistributable:

- `vendor/IodineGBA/`, `vendor/user_scripts/` — **IodineGBA**, a pure-JS GBA
  emulator by Grant Galitz (MIT, see `vendor/IodineGBA.LICENSE`). Used on the
  main thread (no Web Workers / SharedArrayBuffer) so it runs from `file://`.
- `vendor/user_scripts/XAudioJS/` — audio glue (same author, MIT).
- `vendor/driver.js` — our small frontend that boots the core with the inlined
  BIOS + ROM, wires the canvas/keyboard/touch, and replaces IodineGBA's
  menu-heavy default GUI.
- `vendor/gba_bios.bin` — the **Cult-of-GBA** open-source GBA BIOS
  reimplementation (MIT, © 2020–2021 DenSinH and fleroviux; see
  `vendor/gba_bios.LICENSE`). IodineGBA has no BIOS HLE, so a real 16 KB BIOS
  is required; this one is legally redistributable (no Nintendo code).
- `build_player.py` — the bundler.

IodineGBA upstream: https://github.com/taisel/IodineGBA
Open BIOS upstream: https://github.com/Cult-of-GBA/BIOS

## Verification

The build is checked headlessly in CI-style with Node + DOM stubs: FireRed
boots with the bundled BIOS and the shipped `driver.js` renders frames to the
canvas. Final real-device confirmation (speed, audio, visuals) should be done
in an actual browser.
