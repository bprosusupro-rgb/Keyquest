# Keyquest Studio

A standalone Android app that puts a keyboard inside a compatible Ren’Py game. It runs the rebuild and signing on the Quest. The patched game has its own **Keyboard** button and receives SDL key-down and key-up events directly through Ren’Py.

## Use on Quest 3 or 3S

1. Sideload **KeyquestStudio.apk** and open **Keyquest Studio**.
2. Choose a downloaded APK with the file picker or choose an installed single-APK game. The file picker needs an Android document provider. If Quest does not expose one, use the installed-game picker.
3. Confirm that the game uses **Ren’Py 8.4.1**, then choose **Build keyboard APK** and **Save to Downloads**.
4. Sideload `game-keyboard.apk` from Downloads. Open its **Keyboard** button. **S** and **I** are the default shortcuts. **Settings** lets you remap them, switch theme, change size, and dock the keyboard at the top or bottom.

The original file is preserved. Studio preserves the game’s package ID and signs the copy with a new key in Android Keystore. Android may require removing the original installation first because of the signature difference. Back up your saves first. Studio never removes or installs games automatically. Use on APKs you are allowed to modify.

This prerelease targets standard **Ren’Py 8.4.1 universal APKs**. Split packages, script-key-locked builds, custom layouts, and other engine versions are outside its supported scope. Extra UI may be unavailable in games using a custom SDL loop outside Ren’Py screens. The desktop Ren’Py key event and APK signing paths were tested with fixtures. On-device document selection, signing with Android Keystore, and the actual Quest minigame are still unverified.

## Build from source

Run `build.sh path/to/KeyquestStudio.apk` on Linux with Java and zip. Set the following environment variables to absolute paths.

- `ANDROID_JAR` — Android SDK API 35 platform JAR
- `BUILD_TOOLS` — Android SDK Build Tools 35 directory
- `APKSIG_JAR` — Google Maven artifact `com.android.tools.build:apksig:8.7.3`
- `ECJ_JAR` — Eclipse Java compiler 3.39.0
- `SIGNING_KEYSTORE`, `SIGNING_ALIAS`, `SIGNING_PASSWORD` — signing configuration for the Studio APK

The bundled `assets/keyquest_8_4_1.rpyc` is compiled from `game/keyquest_overlay.rpy` by Ren’Py 8.4.1. For a project you can rebuild from source, you can put the `.rpy` in its `game/` folder and use Ren’Py's Android export with the original key.
