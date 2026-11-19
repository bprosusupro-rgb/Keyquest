# Keyquest Studio

A standalone Android app that puts a keyboard inside a compatible Ren’Py game. It runs the rebuild and signing on the Quest. The patched game has its own **Keyboard** button and receives SDL key-down and key-up events directly through Ren’Py.

## Use on Quest 3 or 3S

1. Sideload **KeyquestStudio.apk** and open **Keyquest Studio**.
2. Choose a downloaded APK with the file picker or choose an installed single-APK game. The file picker needs an Android document provider. If Quest does not expose one, use the installed-game picker.
3. Studio scans the selected APK and shows its title, package, app version, and Ren’Py engine version when available. Studio automatically chooses a profile for detected Ren’Py 7.8 and 8.0–8.5 builds. When the usual metadata is absent, Studio also checks loose and cached version modules and compares bundled engine-script fingerprints with official SDKs. A verified fingerprint can select the engine family automatically. Weaker script and Python clues give suggestions. Verify the engine family before selecting it. The Python marker can narrow the choices but cannot identify the exact engine version. A detected unsupported version stays blocked.
4. Sideload the newly named APK from Downloads. Tap the **Keyboard** button in the game’s bottom-right corner. **S** and **I** are the default shortcuts. **Settings** lets you remap them, switch theme, change size, and dock the keyboard at the top or bottom.

### Floating keyboard and updates

Hold **Drag to move** along the top of the keyboard, then move your pointer and release. The game remembers where you leave the keyboard. **Settings** includes **Reset position**, docking, compact mode, and theme options.

To update a patched game, choose its existing APK file or select the installed patched game. Studio detects it, loads the existing add-on selections, and offers **Update keyboard APK**. The update replaces only the known Keyquest scripts and artwork and applies the current add-on choices. Save the new APK to Downloads and install it as an update. In-place installation requires the same Android signing key, which normally means using the same Studio installation on the same headset. Keep your original APK and a save backup.

### Build timeline and output name

Choose an output name before building. Studio uses it for the filename in Downloads and, with the optional **Rename in app library** setting enabled, for the Android launcher label. The original package ID and game launcher artwork are preserved. The rebuilt game has a labeled **Keyboard** button with the Keyquest logo. If the game cannot load the image, the text still opens the keyboard.

The build view shows repacking, adding controls, signing, and verification. During repacking it measures copied bytes and estimates time remaining for that step from the observed copy rate. Signing and verification show the stage instead of a guessed ETA. The final report lists the verified APK size and name. Choose **Change build options** to run a fresh build with another name or add-on selection.

### Macro writer and auto-clicker

Enable **Include macro writer and auto-clicker** in Studio before building. The **Included** line previews what will be added. In the rebuilt game, select **Keyboard → Macros**.

- **Macro writer** appends letters, digits, Space, and Wait to a sequence, with Undo, Clear, step speed, and repeat controls. The draft is saved in the game’s persistent settings.
- **Auto-clicker** asks you to tap a target inside the game, then repeats clicks there at the selected interval and count.
- **Stop automation** stops either tool. Jobs also end when their queue is complete or when a save is loaded.

Automation uses Ren’Py/SDL2 events inside the rebuilt game. It is intended for local gameplay. Target behavior still depends on the game’s input code and the Quest runtime. Ren’Py 8.6 moved to SDL3 and has no bundled profile.

### Smart Input

Enable **Include Smart Input** when building or updating the APK. In the game, open **Keyboard → OCR**. Keep Keyquest Studio installed so the game can use its offline recognition engine.

- **Copy text** reads English on the game screen and types it into the active field. Open the field before scanning.
- **Solve math** reads one arithmetic expression and types the answer. It supports addition, subtraction, multiplication, division, and parentheses. Choose **Top** or **Center** if unrelated text makes it hard to find the problem.
- **Repeat key** sends a key-down and key-up at the chosen interval. Pick a key and press count, then select **Start**. Select **Stop repeat** to end the run early.

**Scan & type** captures one frame after the panel folds away. Studio processes it locally and returns the text to the game. Text and math modes use the game's text-input event, and the game controls which characters it accepts. The Android recognition round trip still needs verification on a Quest headset.

### Optional value editor

Before building, tick **Include local value editor**. In the patched game, tap the corner logo and choose **Values**. Select a suggested value such as `money` or enter the exact variable name. Tap **Edit new value**, enter a number, then tap **Apply value**. Use **Keys** if you need the on-screen keyboard.

The add-on edits existing integer and decimal values in the main Ren’Py store while a local game is running. Variables kept inside objects, dictionaries, another store, or a server are outside its scope. Games can overwrite a value through their own rules. Save in-game if you want the change included in a save and keep a separate backup.

The original file is preserved. Studio preserves the game’s package ID and signs the copy with a new key in Android Keystore. Android may require removing the original installation first because of the signature difference. Back up your saves first. Studio never removes or installs games automatically. Use on APKs you are allowed to modify.

Studio targets standard **Ren’Py universal APKs** from the 7.8 and 8.0 through 8.5 families. Representative SDK versions were tested locally, so compatibility with individual games and patch versions still varies. Split packages, script-key-locked builds, custom layouts, and other engine versions are outside its supported scope. Extra UI may be unavailable in games using a custom SDL loop outside Ren’Py screens. The desktop Ren’Py key event and APK signing paths were tested with fixtures. On-device document selection, signing with Android Keystore, and the actual Quest minigame are still unverified.

## Build from source

Run `build.sh path/to/KeyquestStudio.apk` on Linux with Java and zip. Set the following environment variables to absolute paths.

- `ANDROID_JAR` — Android SDK API 35 platform JAR
- `BUILD_TOOLS` — Android SDK Build Tools 35 directory
- `APKSIG_JAR` — Google Maven artifact `com.android.tools.build:apksig:8.7.3`
- `ECJ_JAR` — Eclipse Java compiler 3.39.0
- `TESSERACT_AAR` — [Tesseract4Android 4.9.0 AAR](https://jitpack.io/cz/adaptech/tesseract4android/tesseract4android/4.9.0/tesseract4android-4.9.0.aar)
- `OCR_ENGLISH_DATA` — [English tessdata_fast model](https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/923915d4ced2a7235221788285785a29c4a42d4a/eng.traineddata)
- `SIGNING_KEYSTORE`, `SIGNING_ALIAS`, `SIGNING_PASSWORD` — signing configuration for the Studio APK

The bundled scripts are compiled with SDKs 7.8.7, 8.0.3, 8.1.3, 8.2.3, 8.3.7, 8.4.1, and 8.5.2. Run `./compile-profile.sh /path/to/renpy-sdk 8_4` to regenerate a profile. For a project you can rebuild from source, copy the overlay script and `assets/keyquest_*.png` into its `game/` folder. Include `game/keyquest_values.rpy` for the editor and `game/keyquest_automation.rpy` for macros and clicks, and `game/keyquest_ocr.rpy` for Smart Input, then export from Ren’Py with the original key. The Studio APK packages the ARM64 OCR libraries used by Quest 3 and 3S. Third-party notices are in `assets/ocr-licenses/`.

## Design

Studio uses an adaptive source-and-build layout, one primary action at a time, and distinct focus and disabled states. The game keyboard uses bordered surfaces and rounded keycaps to stay readable against gameplay. The original logo is `assets/image.png`. Its resized derivatives are used in Studio and in the rebuilt game.

Design references: [Apple layout](https://developer.apple.com/design/human-interface-guidelines/layout), [materials](https://developer.apple.com/design/human-interface-guidelines/materials), [color](https://developer.apple.com/design/human-interface-guidelines/color), and [app icons](https://developer.apple.com/design/human-interface-guidelines/app-icons/).
