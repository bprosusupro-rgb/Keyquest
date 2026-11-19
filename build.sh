#!/usr/bin/env bash
set -euo pipefail
: "${ANDROID_JAR:?Android SDK API 35 android.jar}"
: "${BUILD_TOOLS:?Android SDK Build Tools 35 directory}"
: "${APKSIG_JAR:?apksig-8.7.3.jar}"
: "${ECJ_JAR:?Eclipse Java compiler 3.39.0}"
: "${TESSERACT_AAR:?Tesseract4Android 4.9.0 AAR}"
: "${OCR_ENGLISH_DATA:?tessdata_fast eng.traineddata}"
: "${SIGNING_KEYSTORE:?APK signing key}"
: "${SIGNING_ALIAS:?APK signing alias}"
: "${SIGNING_PASSWORD:?APK signing password}"
export SIGNING_PASSWORD
project="$(cd "$(dirname "$0")" && pwd)"
apk="$(realpath -m "${1:-KeyquestStudio.apk}")"
scratch="$(mktemp -d)"
trap 'rm -rf "$scratch"' EXIT
mkdir -p "$scratch/classes" "$scratch/dex" "$scratch/assets/ocr" "$scratch/lib/arm64-v8a"
cp -a "$project/assets/." "$scratch/assets/"
cp "$OCR_ENGLISH_DATA" "$scratch/assets/ocr/eng.traineddata"
unzip -p "$TESSERACT_AAR" classes.jar > "$scratch/tesseract.jar"
for library in libjpeg.so libleptonica.so libpngx.so libtesseract.so; do
    unzip -p "$TESSERACT_AAR" "jni/arm64-v8a/$library" > "$scratch/lib/arm64-v8a/$library"
done
"$BUILD_TOOLS/aapt2" compile --dir "$project/res" -o "$scratch/resources.zip"
"$BUILD_TOOLS/aapt2" link -I "$ANDROID_JAR" --manifest "$project/AndroidManifest.xml" \
    -A "$scratch/assets" -o "$scratch/unsigned.apk" "$scratch/resources.zip"
mapfile -t sources < <(find "$project/src" -name '*.java' | sort)
java -jar "$ECJ_JAR" -8 -proc:none \
    -bootclasspath "$ANDROID_JAR:$BUILD_TOOLS/core-lambda-stubs.jar" \
    -classpath "$APKSIG_JAR:$scratch/tesseract.jar" -d "$scratch/classes" "${sources[@]}"
mapfile -t classes < <(find "$scratch/classes" -name '*.class')
"$BUILD_TOOLS/d8" --min-api 30 --lib "$ANDROID_JAR" --output "$scratch/dex" "${classes[@]}" "$APKSIG_JAR" "$scratch/tesseract.jar"
zip -q -j "$scratch/unsigned.apk" "$scratch/dex/"*.dex
(cd "$scratch" && zip -q -0 unsigned.apk lib/arm64-v8a/*.so)
"$BUILD_TOOLS/zipalign" -P 16 4 "$scratch/unsigned.apk" "$scratch/aligned.apk"
"$BUILD_TOOLS/apksigner" sign --v4-signing-enabled false --ks "$SIGNING_KEYSTORE" \
    --ks-key-alias "$SIGNING_ALIAS" --ks-pass env:SIGNING_PASSWORD --out "$apk" "$scratch/aligned.apk"
"$BUILD_TOOLS/apksigner" verify "$apk"
"$BUILD_TOOLS/zipalign" -c -P 16 4 "$apk"
