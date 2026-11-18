# Quest Panel Macros

A Godot front end and Android accessibility service for sending screen taps to a selected sideloaded Android app. Select the target once, then run a single tap, a sequence, or repeat a step as an auto-clicker. The target APK needs no companion plugin.

## Install and try a single tap

1. Sideload the arm64 APK with SideQuest or `adb -d install QuestPanelMacros.apk`.
2. Open **Quest Panel Macros** under **Unknown Sources**. If the launcher does not show it, try `adb -d shell am start -n org.questpanel.macros/com.godot.game.GodotAppLauncher`.
3. Open **Android accessibility settings** from the app and enable **Quest Panel Macros**. Availability depends on the headset firmware. If Android marks the sideloaded service as restricted and offers **Allow restricted settings** in the app info menu, you can allow it there and return to accessibility settings.
4. Select the target app or type its Android package name. Keep a harmless screen open for the first test.
5. Enter `50, 50, 500` with one repeat and press **Run in target**. If the target does not open automatically, bring it to the foreground within 30 seconds. The app waits briefly before sending a center tap.

## Tap macros

Each line contains the horizontal position, vertical position, and the delay after that tap. Coordinates are percentages of the focused target window, measured from its top-left corner. Enter two or more lines for a sequence. Use one line with a repeat count above one for an auto-clicker.

```text
50, 75, 500
78, 80, 1000
```

**Find tap point** opens the target and attempts to show a temporary picker. Tap where the macro should act, then return to the controller. If the headset blocks overlays, enter positions manually. The last run's package, tap steps and repeat count are saved locally. Optional text is kept in memory and passed to a compatible focused text field once at the end of the run. Some Ren’Py builds expose an Android text connection when an input prompt is active. Custom canvas input may accept taps while providing no compatible text connection.

Switch away from the target to stop before the next action, or return to the controller and press **Stop**. The app supports up to 30 steps and 100 repeats per run with a ten-minute duration limit. If the target window cannot be inspected or the firmware rejects synthetic gestures on its display, the macro stops. This build targets sideloaded 2D Android panels. It does not emit Meta Touch controller buttons, hardware keycodes or OpenXR actions.

The service can inspect active window information to match targets. It performs actions only after you arm a run and only for the selected app. It does not transmit window data or macro contents.

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

[Android accessibility service reference](https://developer.android.com/reference/android/accessibilityservice/AccessibilityService)
