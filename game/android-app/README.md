# Pokémon Quiz — Android app (WebView wrapper)

This turns the offline single-file player (`../play/PokemonQuiz.html`) into a real
installable Android app: a thin, full-screen WebView with **no internet
permission**, so the whole game runs offline. The math-quiz ROM, emulator,
speed/filter/read-aloud features — everything from the HTML — work unchanged.

## Why this is a project and not a prebuilt .apk
Compiling an `.apk` requires the Android SDK and the Android Gradle Plugin, which
come from Google's Maven repository. The build environment this was developed in
blocks that repository, so the APK can't be produced here. Building it on a normal
machine with **Android Studio** (free) is a two-step process — Android Studio
downloads the SDK automatically.

## Build it (Android Studio — easiest)
1. Install Android Studio.
2. From a terminal in this folder, bundle the game into the app:
   ```
   ./bundle.sh
   ```
   (This runs `../play/build_player.py` and copies the resulting
   `PokemonQuiz.html` into `app/src/main/assets/`.)
3. In Android Studio: **Open** this `android-app` folder. Let it sync (it fetches
   the SDK/plugin on first run).
4. **Build ▸ Build App Bundle(s) / APK(s) ▸ Build APK(s)**.
5. Install the resulting `app/build/outputs/apk/debug/app-debug.apk` on the phone
   (enable "Install unknown apps" for your file manager).

## Build it (command line)
With the Android SDK installed and `ANDROID_HOME`/`local.properties` set:
```
./bundle.sh
./gradlew assembleDebug      # -> app/build/outputs/apk/debug/app-debug.apk
```
`app-debug.apk` is signed with the debug key and installs directly. For a
Play-store-ready signed release, configure a keystore and run `assembleRelease`.

## What's inside
- `app/src/main/java/com/pokequiz/app/MainActivity.java` — full-screen WebView,
  JS + DOM storage enabled, keeps the screen on, loads
  `file:///android_asset/PokemonQuiz.html`.
- `app/src/main/assets/PokemonQuiz.html` — the bundled game (created by `bundle.sh`).
- No `<uses-permission>` entries — the app needs no network or storage access.

## Simpler alternative (no build)
You can skip the APK entirely: open `PokemonQuiz.html` in the phone's browser and
use the browser menu's **Add to Home screen**. The player already ships a web-app
manifest, so the shortcut opens full-screen like an app (it still uses the
browser engine under the hood).
