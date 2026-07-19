#!/bin/bash
# DexPatcher HelloWorld build script — runs in GHA ubuntu-22.04
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TARGET_APK="${1:?Usage: $0 <target.apk> <sdk-dir> [output.apk]}"
SDK="${2:-/usr/local/lib/android/sdk}"
OUTPUT_APK="${3:-/tmp/hg-dexpatcher-helloworld.apk}"
PATCH_DIR="$SCRIPT_DIR/patches"
BUILD_DIR="/tmp/dexpatcher-build"

rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR/classes" "$BUILD_DIR/dex-out" "$BUILD_DIR/apk"

# Step 1: Compile Java patch
echo "==> Finding android.jar..."
ANDROID_JAR=$(find "$SDK/platforms" -name "android.jar" 2>/dev/null | sort -Vr | head -1)
echo "  android.jar: ${ANDROID_JAR:-NOT FOUND}"

echo "==> Compiling patch..."
CP="$PATCH_DIR/lib/dexpatcher-annotation-1.7.0.jar"
[ -n "$ANDROID_JAR" ] && CP="$CP:$ANDROID_JAR"
javac -cp "$CP" -d "$BUILD_DIR/classes" "$PATCH_DIR/src/com/dragon/read/MuteApplicationStub.java"
echo "  ✓ Classes compiled ($(find $BUILD_DIR/classes -name '*.class' | wc -l) classes)"

# Step 2: Convert to DEX
echo "==> Converting to DEX..."
D8=$(find "$SDK/build-tools" -name d8 2>/dev/null | sort -Vr | head -1)
if [ -n "$ANDROID_JAR" ]; then
  "$D8" --lib "$ANDROID_JAR" --min-api 26 --output "$BUILD_DIR/dex-out" \
    "$BUILD_DIR/classes/com/dragon/read/MuteApplicationStub.class"
else
  "$D8" --min-api 26 --output "$BUILD_DIR/dex-out" \
    "$BUILD_DIR/classes/com/dragon/read/MuteApplicationStub.class"
fi
echo "  ✓ DEX: $(ls $BUILD_DIR/dex-out/) ($(wc -c < $BUILD_DIR/dex-out/classes.dex) bytes)"

# Step 3: Apply patches — outputs modified dex files to a directory
echo "==> Applying DexPatcher patches (multi-dex)..."
java -jar "$PATCH_DIR/lib/dexpatcher.jar" \
  --verbose -m \
  -o "$BUILD_DIR/dex-out-modified" \
  "$TARGET_APK" \
  "$BUILD_DIR/dex-out/classes.dex"

echo "  ✓ Patched dex files: $(ls $BUILD_DIR/dex-out-modified/ 2>/dev/null | wc -l)"

# Step 4: Build patched APK — replace dex files in original APK
echo "==> Building patched APK..."
cp "$TARGET_APK" "$BUILD_DIR/apk/patched.apk"
cd "$BUILD_DIR/dex-out-modified"
zip -q -d "$BUILD_DIR/apk/patched.apk" "classes*.dex" 2>/dev/null || true
zip -q -j "$BUILD_DIR/apk/patched.apk" *.dex
cd "$OLDPWD"
cp "$BUILD_DIR/apk/patched.apk" "$OUTPUT_APK"

echo "  ✓ APK: $OUTPUT_APK"
ls -lh "$OUTPUT_APK"
