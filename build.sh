#!/usr/bin/env bash
set -euo pipefail
: "${ANDROID_JAR:?Android SDK API 35 android.jar}"
: "${BUILD_TOOLS:?Android SDK Build Tools 35 directory}"
: "${APKSIG_JAR:?apksig-8.7.3.jar}"
: "${ECJ_JAR:?Eclipse Java compiler 3.39.0}"
: "${SIGNING_KEYSTORE:?APK signing key}"
: "${SIGNING_ALIAS:?APK signing alias}"
: "${SIGNING_PASSWORD:?APK signing password}"
export SIGNING_PASSWORD
project="$(cd "$(dirname "$0")" && pwd)"
apk="$(realpath -m "${1:-KeyquestStudio.apk}")"
scratch="$(mktemp -d)"
trap 'rm -rf "$scratch"' EXIT
mkdir -p "$scratch/classes" "$scratch/dex"
"$BUILD_TOOLS/aapt2" compile --dir "$project/res" -o "$scratch/resources.zip"
"$BUILD_TOOLS/aapt2" link -I "$ANDROID_JAR" --manifest "$project/AndroidManifest.xml" \
    -A "$project/assets" -o "$scratch/unsigned.apk" "$scratch/resources.zip"
mapfile -t sources < <(find "$project/src" -name '*.java' | sort)
java -jar "$ECJ_JAR" -8 -proc:none \
    -bootclasspath "$ANDROID_JAR:$BUILD_TOOLS/core-lambda-stubs.jar" \
    -classpath "$APKSIG_JAR" -d "$scratch/classes" "${sources[@]}"
mapfile -t classes < <(find "$scratch/classes" -name '*.class')
"$BUILD_TOOLS/d8" --min-api 30 --lib "$ANDROID_JAR" --output "$scratch/dex" "${classes[@]}" "$APKSIG_JAR"
zip -q -j "$scratch/unsigned.apk" "$scratch/dex/"*.dex
"$BUILD_TOOLS/zipalign" -P 16 4 "$scratch/unsigned.apk" "$scratch/aligned.apk"
"$BUILD_TOOLS/apksigner" sign --v4-signing-enabled false --ks "$SIGNING_KEYSTORE" \
    --ks-key-alias "$SIGNING_ALIAS" --ks-pass env:SIGNING_PASSWORD --out "$apk" "$scratch/aligned.apk"
"$BUILD_TOOLS/apksigner" verify "$apk"
"$BUILD_TOOLS/zipalign" -c -P 16 4 "$apk"
