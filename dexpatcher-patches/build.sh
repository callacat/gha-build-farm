#!/bin/bash
# DexPatcher HelloWorld build script — runs in GHA ubuntu-22.04
# Extracts dex files, patches individually, replaces in APK
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TARGET_APK="${1:?Usage: $0 <target.apk> <sdk-dir> [output.apk]}"
SDK="${2:-/usr/local/lib/android/sdk}"
OUTPUT_APK="${3:-/tmp/hg-dexpatcher-helloworld.apk}"
PATCH_DIR="$SCRIPT_DIR/patches"
BUILD_DIR="/tmp/dexpatcher-build"

rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR/classes" "$BUILD_DIR/dex-patch" "$BUILD_DIR/dex-orig" "$BUILD_DIR/dex-modified"

# Step 1: Compile Java patch
echo "==> Finding android.jar..."
ANDROID_JAR=$(find "$SDK/platforms" -name "android.jar" 2>/dev/null | sort -Vr | head -1)
echo "  android.jar: ${ANDROID_JAR:-NOT FOUND}"

echo "==> Compiling patch..."
CP="$PATCH_DIR/lib/dexpatcher-annotation-1.7.0.jar"
[ -n "$ANDROID_JAR" ] && CP="$CP:$ANDROID_JAR"
javac -cp "$CP" -d "$BUILD_DIR/classes" "$PATCH_DIR/src/com/dragon/read/MuteApplicationStub.java"
echo "  ✓ Classes compiled ($(find $BUILD_DIR/classes -name '*.class' | wc -l) classes)"

# Step 2: Convert class to DEX
echo "==> Converting to DEX..."
D8=$(find "$SDK/build-tools" -name d8 2>/dev/null | sort -Vr | head -1)
"$D8" --lib "$ANDROID_JAR" --min-api 26 --output "$BUILD_DIR/dex-patch" \
  "$BUILD_DIR/classes/com/dragon/read/MuteApplicationStub.class"
echo "  ✓ Patch DEX: $BUILD_DIR/dex-patch/classes.dex ($(wc -c < $BUILD_DIR/dex-patch/classes.dex) bytes)"

# Step 3: Extract dex files from APK
echo "==> Extracting dex files from APK..."
cd "$BUILD_DIR/dex-orig"
unzip -q "$TARGET_APK" "classes*.dex"
ls -la classes*.dex 2>/dev/null
NUM_DEX=$(ls classes*.dex 2>/dev/null | wc -l)
echo "  Found $NUM_DEX dex files"
cd "$OLDPWD"

# Step 4: Apply dexpatcher to each dex file (non-multi-dex mode = no -m flag)
echo "==> Applying DexPatcher to each dex..."
PATCH_DEX="$BUILD_DIR/dex-patch/classes.dex"
mkdir -p "$BUILD_DIR/dex-modified"
HIT=0
for dex in "$BUILD_DIR/dex-orig"/classes*.dex; do
  name=$(basename "$dex")
  echo "  Processing $name..."
  set +e
  java -jar "$PATCH_DIR/lib/dexpatcher.jar" \
    --verbose \
    -o "$BUILD_DIR/dex-modified/$name" \
    "$dex" \
    "$PATCH_DEX" 2>&1
  RC=$?
  set -e
  if [ $RC -eq 0 ]; then
    echo "    ✓ $name patched"
    HIT=1
  elif [ $RC -eq 3 ]; then
    # Check if it was "no match" vs actual error
    if grep -q "No patch\|not found\|does not exist" <<< "$(java -jar $PATCH_DIR/lib/dexpatcher.jar --dry-run -o /dev/null "$dex" "$PATCH_DEX" 2>&1 || true)"; then
      echo "    - No matching class in $name, copying original"
      cp "$dex" "$BUILD_DIR/dex-modified/$name"
    else
      # Maybe it's a multi-dex embedded APK error, or different issue
      echo "    ⚠ Exit $RC for $name (might not contain target class)"
      cp "$dex" "$BUILD_DIR/dex-modified/$name"
    fi
  fi
done

echo "  Patched dex files: $(ls $BUILD_DIR/dex-modified/*.dex 2>/dev/null | wc -l)"

# Step 5: Rebuild APK — replace dex files
echo "==> Rebuilding APK..."
cp "$TARGET_APK" "$BUILD_DIR/patched.apk"
cd "$BUILD_DIR/dex-modified"
zip -q -d "$BUILD_DIR/patched.apk" "classes*.dex" 2>/dev/null || true
zip -q -j "$BUILD_DIR/patched.apk" *.dex
cd "$OLDPWD"
cp "$BUILD_DIR/patched.apk" "$OUTPUT_APK"

echo "  ✓ APK: $OUTPUT_APK"
ls -lh "$OUTPUT_APK"
echo "  HIT=$HIT (1=patch applied, 0=no match)"
