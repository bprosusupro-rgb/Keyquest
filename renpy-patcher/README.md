# Keyquest in-game keyboard patcher

Adds a **Keyboard** button inside a compatible Ren’Py game. Tap it for a keyboard with dedicated **S** and **I** buttons, letters, digits, Shift, Space, Backspace, and Enter. Buttons post events inside Ren’Py. The patched game runs without Keyquest, an accessibility service, or ADB input injection.

## Build a patched APK

Use a desktop computer with Python 3.9+ (and tkinter for the GUI), a Java JDK on PATH, Android SDK Build Tools 35+, and the **same Ren’Py SDK version as the game**. Use this for games you are allowed to modify.

1. Run `python desktop.py` from this folder.
2. Select the downloaded universal APK, or connect the headset over authorized USB ADB and use **Load list** to select an installed game. Platform Tools must be on PATH. You can also type the installed package name. `adb -d shell pm list packages -3` lists third-party packages.
3. Select the Ren’Py SDK folder, the Android build-tools version folder, and a new output APK filename. Click **Build patched APK**.
4. Sideload the output APK. Open the game and select **Keyboard** in its upper-right corner.

For a command-line build:

```sh
python patch_apk.py --apk game.apk --sdk /path/to/matching-renpy-sdk --build-tools /path/to/android-sdk/build-tools/35.0.0 --output game-keyboard.apk
```

Use `--installed com.example.game` instead of `--apk` to pull one installed package. The original APK file is preserved. The output retains the original Android package name and uses a new signing key saved next to your output. Android will reject an in-place update if the original signer differs. Back up game saves before replacing an existing installation. Uninstalling the original can erase its local saves. The patcher never uninstalls or installs an app.

If you have the original Ren’Py project, copy `keyquest_overlay.rpy` to its `game/` folder and export through Ren’Py. Use the original signing key for an in-place update.

## Compatibility

The patcher accepts single Ren’Py universal APKs with the standard `assets/x-game/` layout. The overlay is compiled using the SDK you choose. Split APKs, script-key-locked projects, and games with a different asset layout are outside this build’s scope. Some custom minigames use an input mechanism other than Ren’Py/pygame key events, and some screens suppress ordinary overlays. The APK you want to patch has not been provided for a game-specific test.
