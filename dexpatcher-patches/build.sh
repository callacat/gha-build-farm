#!/bin/bash
# DexPatcher HelloWorld build script — runs in GHA ubuntu-22.04
# Uses pre-installed Android SDK: /usr/local/lib/android/sdk
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TARGET_APK="${1:?Usage: $0 <target.apk> [output.apk]}"
OUTPUT_APK="${2:-/tmp/hg-dexpatcher-helloworld.apk}"
PATCH_DIR="$SCRIPT_DIR/patches"
BUILD_DIR="/tmp/dexpatcher-build"
SDK="${ANDROID_HOME:-/usr/local/lib/android/sdk}"

rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR/classes" "$BUILD_DIR/dex"

# Step 1: Compile Java patch (need android.jar for Application/Toast)
echo "==> Finding android.jar..."
ANDROID_JAR=$(find "$SDK/platforms" -name "android.jar" 2>/dev/null | sort -Vr | head -1)
echo "  android.jar: ${ANDROID_JAR:-NOT FOUND}"

echo "==> Compiling patch..."
CP="-cp $PATCH_DIR/lib/dexpatcher-annotation-1.7.0.jar"
[ -n "$ANDROID_JAR" ] && CP="$CP:$ANDROID_JAR"

javac $CP \
  -d "$BUILD_DIR/classes" \
  "$PATCH_DIR/src/com/dragon/read/MuteApplicationStub.java"
echo "  ✓ Classes compiled"

# Step 2: Convert to DEX using d8
echo "==> Converting to DEX..."
D8=$(find "$SDK/build-tools" -name d8 2>/dev/null | sort -Vr | head -1)

if [ -n "$ANDROID_JAR" ]; then
  "$D8" --lib "$ANDROID_JAR" --min-api 26 --output "$BUILD_DIR/dex" \
    "$BUILD_DIR/classes/com/dragon/read/MuteApplicationStub.class"
else
  "$D8" --min-api 26 --output "$BUILD_DIR/dex" \
    "$BUILD_DIR/classes/com/dragon/read/MuteApplicationStub.class"
fi

echo "  ✓ DEX: $BUILD_DIR/dex/classes.dex ($(wc -c < $BUILD_DIR/dex/classes.dex) bytes)"

# Step 3: Apply patches with dexpatcher (multi-dex enabled)
echo "==> Applying DexPatcher patches..."
java -jar "$PATCH_DIR/lib/dexpatcher.jar" \
  --verbose -J \
  -o "$OUTPUT_APK" \
  "$TARGET_APK" \
  "$BUILD_DIR/dex/classes.dex"

echo "  ✓ Patched APK: $OUTPUT_APK ($(wc -c < "$OUTPUT_APK") bytes)"
ls -lh "$OUTPUT_APK"
