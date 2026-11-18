# Keyquest

A Godot control panel and Android accessibility service for a sideloaded 2D game on Meta Quest 3 or 3S. Keyquest adds an in-game keyboard, tap macros, and repeat tapping.

## Install and open the keyboard

1. Sideload the signed ARM64 APK with SideQuest or `adb -d install -r QuestPanelMacros.apk`. The package name and signing key stay the same as v0.1.0.
2. Open **Keyquest** under **Unknown Sources**. If the launcher does not show it, try `adb -d shell am start -n org.questpanel.macros/com.godot.game.GodotAppLauncher`.
3. Select **Enable accessibility service**, then enable **Keyquest** in Android accessibility settings. **Open in-game keyboard** and the macro controls also open system settings when the service is disabled. If Android offers **Allow restricted settings** in the app info menu, enable it for Keyquest, then return to the accessibility screen. The **Service connected** label confirms that Android started the service.
4. Choose your installed game or type its Android package name. Select **Open in-game keyboard**. If Keyquest cannot launch the game, switch to it within 30 seconds.
5. Focus a text prompt in the game and press a few keyboard keys. Use **Move up** or **Move down** if the keyboard covers the field. The keyboard closes when you switch to another app.

Keyquest uses Android's accessibility input connection on Android 13 or newer. The keyboard provides letters, Shift, numbers, punctuation, Space, Backspace, and Enter. The target game must expose an Android text input connection while its prompt is active. An older or custom Ren’Py build can accept a physical keyboard while exposing no compatible input connection for this overlay. Horizon OS can also limit which Android windows and overlay types are available.

If the keyboard cannot send text, try a paired physical keyboard with the in-game prompt focused. On a USB-debugging connection, a computer can also try `scrcpy --no-video --no-audio --keyboard=uhid` to send input as a physical keyboard. If you can rebuild the game, test its own Android text-input request and the Quest keyboard manifest feature in that build.

## Tap macros

Each line contains the horizontal position, vertical position, and the delay after that tap. Coordinates are percentages of the focused target window, measured from its top-left corner. Enter two or more lines for a sequence. Use one line with a repeat count above one for an auto-clicker.

```text
50, 75, 500
78, 80, 1000
```

**Find tap point** opens the target and attempts to show a temporary picker. Tap where the macro should act, then return to the controller. If the headset blocks overlays, enter positions manually. The last run's package, tap steps and repeat count are saved locally. Optional text is kept in memory and passed to a compatible focused text field once at the end of the run. Some Ren’Py builds expose an Android text connection when an input prompt is active. Custom canvas input may accept taps while providing no compatible text connection.

Switch away from the target to stop before the next action, or return to the controller and press **Stop**. The app supports up to 30 steps and 100 repeats per run with a ten-minute duration limit. If the target window cannot be inspected or the firmware rejects synthetic gestures on its display, the macro stops. This build targets sideloaded 2D Android panels. The macro runner simulates touch events. Meta Touch buttons and OpenXR actions are outside its scope.

The service can inspect active window information to match targets. It acts only after you start a keyboard session or macro, and only for the selected app. Keyboard input goes straight to the game and is kept out of saved macro settings. It does not transmit window data or macro contents.

## Build from source

Install Godot 4.6.3 and its matching export templates. Set the Java and Android SDK locations in Godot's editor settings. The Godot project exports the base app. The packaging script adds the plugin DEX and accessibility service manifest, then aligns and signs the final APK.

The packaging script takes these environment variables. Use absolute paths.

| Variable | Value |
| --- | --- |
| `APKTOOL_JAR` | Apktool 2.12.1 |
| `ECJ_JAR` | Eclipse Java compiler 3.39.0 |
| `GODOT_AAR` | Maven artifact `org.godotengine:godot:4.6.3.stable` with `.aar` extension |
| `ANDROID_JAR` | Android SDK API 35 platform JAR |
| `BUILD_TOOLS` | Android SDK build tools 35 or newer |
| `SIGNING_KEYSTORE`, `SIGNING_ALIAS`, `SIGNING_PASSWORD` | Your own Android signing key details |
| `GODOT` | Optional explicit path to the Godot binary |

Run `native/build-apk.sh QuestPanelMacros.apk` from a Linux environment with Java, Python, zip, and unzip. Sign subsequent builds with the same key to install them as updates.

The APK signature, resources, and service registration were checked locally. Quest firmware behavior and the Ren’Py target still need a headset test.

[Meta 2D app and manifest guidance](https://developers.meta.com/vr/documentation/android-apps/port-an-existing-app/) · [Android accessibility input connection](https://developer.android.com/reference/android/accessibilityservice/InputMethod.AccessibilityInputConnection) · [Ren’Py Android input support](https://www.renpy.org/doc/html/android.html) · [scrcpy physical keyboard mode](https://github.com/Genymobile/scrcpy/blob/master/doc/keyboard.md)
