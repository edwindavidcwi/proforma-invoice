# Pokemon Quiz - Windows app

An [Electron](https://www.electronjs.org/) wrapper that turns the offline
Pokemon Quiz game into a normal Windows desktop app (its own window, Start-menu
and desktop shortcuts), installed via a standard `Setup.exe`.

The game is the single self-contained `assets/PokemonQuiz.html` (Game Boy ROM,
emulator, and UI all inlined into one file), produced by `../play/build_player.py`.
It needs no internet at runtime.

## How it's built
You normally don't build this by hand - the **Build Pokemon Quiz apps** GitHub
Actions workflow (`.github/workflows/build-apk.yml`) builds it on a Windows
runner and publishes `PokemonQuiz-Windows-Setup.exe` to the `pokemon-quiz-app`
release.

## Building locally (on Windows, needs Node.js)
```sh
# 1. generate the game file (needs Python + the built ROM)
python ..\play\build_player.py --out assets\PokemonQuiz.html
# 2. install deps and build the installer
npm install
npm run dist
# installer appears in dist\Pokemon Quiz Setup 1.0.0.exe
```

To just run it without packaging: `npm install && npm start`.
