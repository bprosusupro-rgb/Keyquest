# Keyquest Studio

A standalone Android app that puts a keyboard inside a compatible Ren’Py game. It runs the rebuild and signing on the Quest. The patched game has its own **Keyboard** button and receives SDL key-down and key-up events directly through Ren’Py.

## Use on Quest 3 or 3S

1. Sideload **KeyquestStudio.apk** and open **Keyquest Studio**.
2. Choose a downloaded APK with the file picker or choose an installed single-APK game. The file picker needs an Android document provider. If Quest does not expose one, use the installed-game picker.
3. Studio scans the selected APK and shows its title, package, app version, and Ren’Py engine version when available. A detected Ren’Py 8.4.1 build is ready automatically. If the engine version is unknown, confirm 8.4.1 manually before choosing **Build APK** and **Save to Downloads**. A detected unsupported version stays blocked.
4. Sideload `game-keyboard.apk` from Downloads. Tap the **Keyquest logo** in the game’s bottom-right corner. **S** and **I** are the default shortcuts. **Settings** lets you remap them, switch theme, change size, and dock the keyboard at the top or bottom.

### Optional value editor

Before building, tick **Include local value editor**. In the patched game, tap the corner logo and choose **Values**. Select a suggested value such as `money` or enter the exact variable name. Tap **Edit new value**, enter a number, then tap **Apply value**. Use **Keys** if you need the on-screen keyboard.

The add-on edits existing integer and decimal values in the main Ren’Py store while a local game is running. Variables kept inside objects, dictionaries, another store, or a server are outside its scope. Games can overwrite a value through their own rules. Save in-game if you want the change included in a save and keep a separate backup.

The original file is preserved. Studio preserves the game’s package ID and signs the copy with a new key in Android Keystore. Android may require removing the original installation first because of the signature difference. Back up your saves first. Studio never removes or installs games automatically. Use on APKs you are allowed to modify.

This prerelease targets standard **Ren’Py 8.4.1 universal APKs**. Split packages, script-key-locked builds, custom layouts, and other engine versions are outside its supported scope. Extra UI may be unavailable in games using a custom SDL loop outside Ren’Py screens. The desktop Ren’Py key event and APK signing paths were tested with fixtures. On-device document selection, signing with Android Keystore, and the actual Quest minigame are still unverified.

## Build from source

Run `build.sh path/to/KeyquestStudio.apk` on Linux with Java and zip. Set the following environment variables to absolute paths.

- `ANDROID_JAR` — Android SDK API 35 platform JAR
- `BUILD_TOOLS` — Android SDK Build Tools 35 directory
- `APKSIG_JAR` — Google Maven artifact `com.android.tools.build:apksig:8.7.3`
- `ECJ_JAR` — Eclipse Java compiler 3.39.0
- `SIGNING_KEYSTORE`, `SIGNING_ALIAS`, `SIGNING_PASSWORD` — signing configuration for the Studio APK

The bundled `assets/keyquest_8_4_1.rpyc` is compiled from `game/keyquest_overlay.rpy` by Ren’Py 8.4.1. For a project you can rebuild from source, copy the overlay script and `assets/keyquest_*.png` into its `game/` folder. Include `game/keyquest_values.rpy` for the optional editor, then export from Ren’Py with the original key.

## Design

Studio uses an adaptive source-and-build layout, one primary action at a time, and distinct focus and disabled states. The game keyboard uses bordered surfaces and rounded keycaps to stay readable against gameplay. The original logo is `assets/image.png`. Its resized derivatives are used in Studio and in the rebuilt game.

Design references: [Apple layout](https://developer.apple.com/design/human-interface-guidelines/layout), [materials](https://developer.apple.com/design/human-interface-guidelines/materials), [color](https://developer.apple.com/design/human-interface-guidelines/color), and [app icons](https://developer.apple.com/design/human-interface-guidelines/app-icons/).
