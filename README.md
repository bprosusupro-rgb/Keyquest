# Keyquest Studio

A standalone Android app that puts a keyboard inside a compatible Ren’Py game. It runs the rebuild and signing on the Quest. The patched game has its own **Keyboard** button and receives SDL key-down and key-up events directly through Ren’Py.

## Use on Quest 3 or 3S

1. Sideload **KeyquestStudio.apk** and open **Keyquest Studio**.
2. Choose a downloaded APK with the file picker or choose an installed single-APK game. The file picker needs an Android document provider. If Quest does not expose one, use the installed-game picker.
3. Studio scans the selected APK and shows its title, package, app version, and Ren’Py engine version when available. Studio automatically chooses a profile for detected Ren’Py 7.5, 7.8, and 8.0–8.5 builds. When the usual metadata is absent, Studio also checks loose and cached version modules and compares bundled engine-script fingerprints with official SDKs. A verified fingerprint can select the engine family automatically. Weaker script and Python clues give suggestions. Verify the engine family before selecting it. The Python marker can narrow the choices but cannot identify the exact engine version. A detected unsupported version stays blocked.
4. Sideload the newly named APK from Downloads. Tap the **Keyboard** button in the game’s bottom-right corner. **S** and **I** are the default shortcuts. **Settings** lets you remap them, switch theme, change size, and dock the keyboard at the top or bottom.

### Floating keyboard and updates

Hold **Drag to move** in a panel’s title bar, then move your pointer and release. The keyboard, OCR settings, OCR results, live OCR, repeat controls, macros, auto-clicker, and values editor each remember their own position. Drag the grip beside the **Keyboard** launcher to move it, or tap **Keyboard** to open it. **Keyboard → Settings → Reset positions** restores the default locations. Settings also include keyboard docking, compact mode, and theme options.

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

Enable **Include Smart Input** when building or updating the APK. In the game, open **Keyboard → OCR**. The rebuilt game includes an offline Tesseract neural OCR model. Keep Studio installed for the one-shot fallback on older runtimes.

- **Copy text** reads English on the game screen. **Show result** displays it in the game, and **Type in game** sends it to the active text field.
- **Solve math** reads one arithmetic expression and offers the same output options. It supports addition, subtraction, multiplication, division, and parentheses. Choose **Bottom** for math problems displayed under the answer choices, or another area that contains the equation.
- **Repeat keys** runs one key or several in the order you enter them. Set the interval and loop count, then select **Start**. **Read keys** can fill the sequence from a visible prompt such as “Press S and I rapidly.” Check the detected keys before starting. When the prompt changes, select **Edit keys** to stop the current repeat and scan again or enter different keys. **Stop repeat** ends the run.

**Typing challenge** under **OCR → Copy text** scans a wide area around the lower prompt box. **Full screen** reads the whole frame and checks the lower area again when it cannot isolate a challenge sentence. Both can join wrapped lines above the “Type the line above” instruction. Use **Show result** to review longer text in a scrollable preview. Clear the game’s text field before retrying a scan and press Enter after checking what was typed.

**Race assist** starts fast key presses and scans the upper-middle banner more often. It follows a new readable cue immediately and allows one brief missed scan. **Area: Race** focuses OCR on upper-middle prompts such as “Press S rapidly” on a striped race track. **Follow key prompts** recognizes new key cues while the game is open, cycles through the detected keys at the chosen interval, and stops sending keys when no cue is recognized. **Watch for answers** updates the displayed result as visible arithmetic changes. Both live modes pause while you drag a Keyquest panel, then scan fresh on release. They scan periodically, work best with a small scan area, and stop after one minute or when you tap **Stop OCR**.

**Scan & show** and **Scan & type** capture one frame after the panel hides. Recognition runs locally in the game process when supported. **Type in game** uses the active game field’s text-input event and respects its character limits. The Android recognition round trip still needs verification on a Quest headset.

### Color memory and picture tiles

Open **Keyboard → OCR → Minigame helpers**. Each helper remembers its own board corners. Mark the upper-left and lower-right of the entire game board and move the floating controls clear of it.

- **Color memory** supports the red, blue, green and yellow grid. Select **Record flashes** before the first flash, while all four pads are idle. When the game asks for the sequence, select **Finish recording**. Check or edit the sequence, then select **Play sequence**.
- **Picture tiles** supports 3 × 3 and 4 × 4 sliding pictures with one dark empty slot and a goal blank in the bottom-right. Select the grid size before setting the board corners. Each size saves its own calibration. Select **Scan tiles** to match picture edges. On a numbered board, Keyquest tries to read every label and checks that the order is reachable. On a 4 × 4 board, review the proposed picture before selecting **Plan moves**. Tap two tiles to swap them, or choose **Set number order** and tap the tiles labeled 1 through 15 in sequence. **Play one move** and **Play all moves** click the planned tiles and verify the board before advancing. During tile scanning and playback, Keyquest hides its launcher and parks a compact Stop button outside the board. If the board fills the screen, use the game-menu key to stop. If a tap is ignored, Keyquest retries once after confirming the board stayed still. It replans when it recognizes a different legal tile arrangement.

I used the Quest screenshots to check color positions and picture reconstruction. A timed color round and game input on the headset still need verification.

### Optional value editor

Before building, tick **Include local value editor**. In the patched game, tap the corner logo and choose **Values**. Browse or search game values, including nested fields such as `player.coins` and named stores such as `store.economy.balance`. Use **ABC** to search with the Quest controller, or enter an exact path with **Edit search**. Select a value, enter the replacement on the number pad, then tap **Apply value**. Use **Refresh list** if the game creates new variables after you open the panel.

The add-on edits existing integer and decimal values in the main Ren’Py store while a local game is running. Variables kept inside objects, dictionaries, another store, or a server are outside its scope. Games can overwrite a value through their own rules. Save in-game if you want the change included in a save and keep a separate backup.

The original file is preserved. Studio preserves the game’s package ID and signs the copy with a new key in Android Keystore. Android may require removing the original installation first because of the signature difference. Back up your saves first. Studio never removes or installs games automatically. Use on APKs you are allowed to modify.

Studio targets standard **Ren’Py universal APKs** from the 7.5, 7.8, and 8.0 through 8.5 families. Representative SDK versions were tested locally, so compatibility with individual games and patch versions still varies. Split packages, script-key-locked builds, custom layouts, and other engine versions are outside its supported scope. Extra UI may be unavailable in games using a custom SDL loop outside Ren’Py screens. The desktop Ren’Py key event and APK signing paths were tested with fixtures. On-device document selection, signing with Android Keystore, and the actual Quest minigame are still unverified.

### Diagnostics

Enable **Include diagnostics logging** when updating a game. In the rebuilt game, open **Keyboard → Settings → Diagnostics** and select **Start fresh log**. Reproduce the issue, then select **Turn off logging** to flush and close the file. Turning logging off on Quest exports through Studio. You can also select **Save to Downloads** during or after recording. If Downloads is unavailable, Studio opens the system save picker. The file appears under Downloads as `Keyquest-<game-package>.log.txt`.

Keyquest keeps one log per game. Starting a fresh log replaces the previous one. If logging stays enabled through a restart, the game appends so the previous session's crash details remain available. The game records privately first, so an export failure leaves the log available to retry. At 192 KiB the private log resets. It records scene labels, focus changes, Ren’Py exception types and locations, and Keyquest actions. It excludes dialogue, typed and recognized text, screenshots, and values entered in the editor.

## Build from source

Run `build.sh path/to/KeyquestStudio.apk` on Linux with Java and zip. Set the following environment variables to absolute paths.

- `ANDROID_JAR` — Android SDK API 35 platform JAR
- `BUILD_TOOLS` — Android SDK Build Tools 35 directory
- `APKSIG_JAR` — Google Maven artifact `com.android.tools.build:apksig:8.7.3`
- `ECJ_JAR` — Eclipse Java compiler 3.39.0
- `TESSERACT_AAR` — [Tesseract4Android 4.9.0 AAR](https://jitpack.io/cz/adaptech/tesseract4android/tesseract4android/4.9.0/tesseract4android-4.9.0.aar)
- `OCR_ENGLISH_DATA` — [English tessdata_fast model](https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/923915d4ced2a7235221788285785a29c4a42d4a/eng.traineddata)
- `SIGNING_KEYSTORE`, `SIGNING_ALIAS`, `SIGNING_PASSWORD` — signing configuration for the Studio APK

The bundled scripts are compiled with SDKs 7.5.2, 7.8.7, 8.0.3, 8.1.3, 8.2.3, 8.3.7, 8.4.1, and 8.5.2. Run `./compile-profile.sh /path/to/renpy-sdk 8_4` to regenerate a profile. For a project you can rebuild from source, copy the overlay script and `assets/keyquest_*.png` into its `game/` folder. Include `game/keyquest_values.rpy` for the editor and `game/keyquest_automation.rpy` for macros and clicks, and `game/keyquest_ocr.rpy` for Smart Input, then export from Ren’Py with the original key. The Studio APK packages the ARM64 OCR libraries used by Quest 3 and 3S. Third-party notices are in `assets/ocr-licenses/`.

## Design

Studio uses an adaptive source-and-build layout, one primary action at a time, and distinct focus and disabled states. The game keyboard uses bordered surfaces and rounded keycaps to stay readable against gameplay. The original logo is `assets/image.png`. Its resized derivatives are used in Studio and in the rebuilt game.

Design references: [Apple layout](https://developer.apple.com/design/human-interface-guidelines/layout), [materials](https://developer.apple.com/design/human-interface-guidelines/materials), [color](https://developer.apple.com/design/human-interface-guidelines/color), and [app icons](https://developer.apple.com/design/human-interface-guidelines/app-icons/).
