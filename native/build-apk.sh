#!/usr/bin/env bash
set -euo pipefail

: "${APKTOOL_JAR:?Path to Apktool 2.12.1}"
: "${ECJ_JAR:?Path to Eclipse compiler 3.39.0}"
: "${GODOT_AAR:?Path to Godot 4.6.3.stable Android AAR}"
: "${ANDROID_JAR:?Path to Android SDK platforms/android-35/android.jar}"
: "${BUILD_TOOLS:?Path to Android SDK build-tools directory, version 35 or newer}"
: "${SIGNING_KEYSTORE:?Path to APK signing keystore}"
: "${SIGNING_ALIAS:?Keystore alias}"
: "${SIGNING_PASSWORD:?Keystore password}"
export SIGNING_PASSWORD

project="$(cd "$(dirname "$0")/.." && pwd)"
apk="$(realpath -m "${1:-QuestPanelMacros.apk}")"
mkdir -p "$(dirname "$apk")"
scratch="$(mktemp -d)"
trap 'rm -rf "$scratch"' EXIT
mkdir -p "$scratch/classes" "$scratch/dex"
apktool() {
    java -jar "$APKTOOL_JAR" "$@"
}

"${GODOT:-godot}" --headless --path "$project" \
    --export-debug Android "$scratch/base.apk"
apktool d -s -p "$scratch/framework" -o "$scratch/decoded" "$scratch/base.apk"
python3 "$project/native/patch_manifest.py" "$scratch/decoded/AndroidManifest.xml"
mkdir -p "$scratch/decoded/res/xml"
cp "$project/native/GODOT-LICENSE.txt" "$project/native/GODOT-COPYRIGHT.txt" "$scratch/decoded/assets/"
cp "$project/native/res/xml/macro_accessibility.xml" "$scratch/decoded/res/xml/"
unzip -p "$GODOT_AAR" classes.jar > "$scratch/godot.jar"
mapfile -t sources < <(find "$project/native/src" -name '*.java')
java -jar "$ECJ_JAR" -8 -proc:none \
    -bootclasspath "$ANDROID_JAR:$BUILD_TOOLS/core-lambda-stubs.jar" \
    -classpath "$scratch/godot.jar" -d "$scratch/classes" "${sources[@]}"
mapfile -t classes < <(find "$scratch/classes" -name '*.class')
"$BUILD_TOOLS/d8" --min-api 24 --lib "$ANDROID_JAR" \
    --classpath "$scratch/godot.jar" --output "$scratch/dex" "${classes[@]}"
dex_number=2
while [[ -e "$scratch/decoded/classes${dex_number}.dex" ]]; do
    ((dex_number += 1))
done
cp "$scratch/dex/classes.dex" "$scratch/decoded/classes${dex_number}.dex"
apktool b -p "$scratch/framework" "$scratch/decoded" -o "$scratch/unsigned.apk"
if ! unzip -Z1 "$scratch/unsigned.apk" | grep -Fx "classes${dex_number}.dex"; then
    cp "$scratch/dex/classes.dex" "$scratch/classes${dex_number}.dex"
    zip -q -j "$scratch/unsigned.apk" "$scratch/classes${dex_number}.dex"
fi
"$BUILD_TOOLS/zipalign" -P 16 4 "$scratch/unsigned.apk" "$scratch/aligned.apk"
"$BUILD_TOOLS/apksigner" sign --v4-signing-enabled false --ks "$SIGNING_KEYSTORE" \
    --ks-key-alias "$SIGNING_ALIAS" --ks-pass env:SIGNING_PASSWORD --out "$apk" "$scratch/aligned.apk"
"$BUILD_TOOLS/apksigner" verify "$apk"
"$BUILD_TOOLS/zipalign" -c -P 16 4 "$apk"
