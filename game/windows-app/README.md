# Pokemon Quiz - Windows app

An [Electron](https://www.electronjs.org/) wrapper that turns the offline
Pokemon Quiz game into a normal Windows desktop app in its own window. It builds
as a **portable single `.exe`**: no installation, no admin rights, nothing added
to the PC - just double-click `PokemonQuiz-Windows.exe` to play, every time.

The game is the single self-contained `assets/PokemonQuiz.html` (Game Boy ROM,
emulator, and UI all inlined into one file), produced by `../play/build_player.py`.
It needs no internet at runtime.

## Icon / logo
The app icon is an original mark (a graduation cap + star in the game's
blue/purple/gold palette - no copyrighted Pokemon art). Regenerate it with:
```sh
python3 make_icon.py   # needs Pillow: pip install Pillow
```
This writes `build/icon.ico` (the Windows app icon), `build/logo.png` (a 512px
logo for reuse), and `assets/icon.png` (the runtime window/taskbar icon).

## How it's built
You normally don't build this by hand - the **Build Pokemon Quiz apps** GitHub
Actions workflow (`.github/workflows/build-apk.yml`) builds it on a Windows
runner and publishes `PokemonQuiz-Windows.exe` to the `pokemon-quiz-app` release.

## Building locally (on Windows, needs Node.js)
```sh
# 1. generate the game file (needs Python + the built ROM)
python ..\play\build_player.py --out assets\PokemonQuiz.html
# 2. install deps and build the portable .exe
npm install
npm run dist
# the portable app appears at dist\PokemonQuiz-Windows.exe
```

To just run it without packaging: `npm install && npm start`.
