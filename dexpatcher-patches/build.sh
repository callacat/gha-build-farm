#!/bin/bash
# DexPatcher HelloWorld build script — runs in GHA ubuntu-22.04
# Uses apktool for clean APK rebuild (not zip injection)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TARGET_APK="${1:?Usage: $0 <target.apk> <sdk-dir> [output.apk]}"
SDK="${2:-/usr/local/lib/android/sdk}"
OUTPUT_APK="${3:-/tmp/hg-dexpatcher-helloworld.apk}"
PATCH_DIR="$SCRIPT_DIR/patches"
BUILD_DIR="/tmp/dexpatcher-build"

rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR/classes" "$BUILD_DIR/dex-patch" "$BUILD_DIR/dex-orig"

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
echo "  ✓ Patch DEX: $(wc -c < $BUILD_DIR/dex-patch/classes.dex) bytes"

# Step 3: Apply dexpatcher to APK (directly, without -m for single dex at a time)
echo "==> Applying DexPatcher patch to target APK..."
java -jar "$PATCH_DIR/lib/dexpatcher.jar" \
  --verbose \
  -o "$BUILD_DIR/patched.apk" \
  "$TARGET_APK" \
  "$BUILD_DIR/dex-patch/classes.dex" 2>&1 || true
# ^ This will fail on multi-dex but we catch it

# If dexpatcher succeeded directly (non-multi-dex = not many classes.dex):
if [ -f "$BUILD_DIR/patched.apk" ] && [ "$(stat -c%s "$BUILD_DIR/patched.apk" 2>/dev/null || echo 0)" -gt 1024 ]; then
  cp "$BUILD_DIR/patched.apk" "$OUTPUT_APK"
  echo "  ✓ Direct patch succeeded"
  ls -lh "$OUTPUT_APK"
  exit 0
fi

# Fallback: multi-dex APK - use apktool decode/rebuild
echo "  Multi-dex APK detected, using apktool decode/rebuild flow..."
echo "==> Decoding APK with apktool..."
APKTOOL=$(which apktool 2>/dev/null || find "$SDK" -name apktool.jar 2>/dev/null | head -1)
if [ -z "$APKTOOL" ]; then
  # Install apktool
  echo "  Installing apktool..."
  curl -sL "https://github.com/iBotPeaches/Apktool/releases/download/v3.0.2/apktool_3.0.2.jar" -o /opt/apktool.jar
  APKTOOL="/opt/apktool.jar"
fi

java -jar "$APKTOOL" -q d "$TARGET_APK" -o "$BUILD_DIR/apktool_out" -f
echo "  ✓ APK decoded"

# Extract dex files from decoded APK
# In apktool 3.x, dex files are in unknown/ directory or root
echo "==> Patching individual dex files..."
for dex in "$BUILD_DIR/apktool_out"/classes*.dex; do
  [ -f "$dex" ] || continue
  name=$(basename "$dex")
  echo "  Processing $name..."
  set +e
  java -jar "$PATCH_DIR/lib/dexpatcher.jar" --verbose \
    -o "$BUILD_DIR/$name" \
    "$dex" \
    "$BUILD_DIR/dex-patch/classes.dex" 2>/dev/null
  RC=$?
  set -e
  if [ $RC -eq 0 ] && [ -f "$BUILD_DIR/$name" ]; then
    echo "    ✓ $name patched, replacing..."
    cp "$BUILD_DIR/$name" "$dex"
  else
    echo "    - No match in $name, keeping original"
  fi
done

# Rebuild APK with apktool
echo "==> Rebuilding APK..."
cd "$BUILD_DIR/apktool_out"
java -jar "$APKTOOL" b . -o "$BUILD_DIR/unsigned.apk" 2>&1
cd "$OLDPWD"

if [ -f "$BUILD_DIR/unsigned.apk" ]; then
  cp "$BUILD_DIR/unsigned.apk" "$OUTPUT_APK"
  echo "  ✓ APK rebuilt with apktool"
else
  echo "  ERROR: apktool rebuild failed"
  exit 1
fi

echo ""
ls -lh "$OUTPUT_APK"
