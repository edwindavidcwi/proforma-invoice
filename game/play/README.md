# Play the Pokémon Quiz game — offline, one file

This folder builds a **single, self-contained `.html` file** that plays the
educational Pokémon Quiz ROM in any modern browser, **fully offline**. The
emulator (WebAssembly + JavaScript) and the game ROM are baked *inside* the
HTML, so there is nothing to install and nothing to download at run time.

> One file = easy to share. Email it, drop it in a shared drive, or copy it to a
> USB stick / phone. Each student just opens the same file and plays.

The generated file is committed here as **`PokemonQuiz.html`**.

---

## Quick start

### On Windows (or Mac / Linux desktop)
1. Copy **`PokemonQuiz.html`** to the computer.
2. Double-click it. It opens in the default browser and the game starts.
3. Controls (keyboard):

   | Key | Game Boy button |
   |-----|-----------------|
   | Arrow keys | D-pad (move) |
   | `Z` | B |
   | `X` | A |
   | `Enter` | Start |
   | `Tab` | Select |
   | `Shift` | Fast-forward (hold) |
   | `Backspace` | Rewind (hold) |
   | `F6` / `F9` | Save / load state |

   The toolbar also has **Save**, **Load**, **Fullscreen**, and **Open ROM**
   buttons.

### On Android
You have two offline options:

**A. The same single file in a browser.** Copy `PokemonQuiz.html` to the phone
(Downloads folder is fine) and open it from a browser that allows local files —
**Firefox for Android** works well (open `file:///sdcard/Download/PokemonQuiz.html`).
On-screen touch controls (D-pad + A/B/Start/Select) appear automatically on
touch devices. Once it has loaded once, it keeps working with no internet.

> Note: Chrome for Android restricts opening local `file://` pages. If you only
> have Chrome, use option B, or host the file on any simple web server.

**B. A native open-source emulator (most reliable on Android).** Install an
open-source Game Boy Color emulator and load the raw ROM
`../pokered/pokered.gbc`:
- **mGBA** — open source (MPL-2.0), available for Android and Windows.
- **GBC.emu** — open source (GPL), Android.

Native emulators give you the best performance, save files, and controller
support. Use the **same `pokered.gbc`** on every device.

---

## Rebuilding after you change the game

Whenever the ROM is rebuilt (`cd ../pokered && make`), regenerate the player so
it contains the latest game:

```sh
cd game/play
python3 build_player.py
```

Options:

```
python3 build_player.py --rom ../pokered/pokered.gbc \
                        --out PokemonQuiz.html \
                        --title "Pokemon Quiz"
```

The script base64-encodes the ROM and the emulator WASM and writes one HTML
document. No build tools beyond Python 3 are required.

The **Open ROM** button (or drag-and-drop) also lets the same player load any
other `.gb` / `.gbc` file at run time — handy for trying a fresh build without
rebuilding the HTML.

---

## What's inside / licensing

The emulator is **binjgb** by Ben Smith, used unmodified as a prebuilt core:

- `vendor/binjgb.js`, `vendor/binjgb.wasm` — the emulator (MIT,
  see `vendor/binjgb.LICENSE`).
- `vendor/player.js` — a small wrapper adapted from binjgb's `docs/simple.js`
  (MIT). Changes: the WASM and ROM are supplied inline so it runs offline from
  `file://`, plus on-screen buttons and a ROM file picker. See the header
  comment in that file for details.
- The on-screen gamepad styling originates from **GB Studio** by Chris Maltby
  (MIT, see `vendor/binjgb.LICENSE.gbstudio`).
- `build_player.py` — the bundler that produces `PokemonQuiz.html`.

binjgb upstream: https://github.com/binji/binjgb
