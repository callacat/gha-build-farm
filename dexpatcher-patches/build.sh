#!/bin/bash
# DexPatcher build → apktool rebuild (可靠方案)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TARGET_APK="${1:?Usage: $0 <target.apk> <sdk-dir> [output.apk]}"
SDK="${2:-/usr/local/lib/android/sdk}"
OUTPUT_APK="${3:-/tmp/hg-dexpatcher-helloworld.apk}"
PATCH_DIR="$SCRIPT_DIR/patches"
BUILD_DIR="/tmp/dexpatcher-build"
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR/classes" "$BUILD_DIR/dex-patch"

echo "==> Finding android.jar..."
ANDROID_JAR=$(find "$SDK/platforms" -name "android.jar" 2>/dev/null | sort -Vr | head -1)
echo "  android.jar: ${ANDROID_JAR:-NOT FOUND}"

echo "==> Compiling patches..."
find "$PATCH_DIR/src" -name "*.java" -print > "$BUILD_DIR/sources.txt"
CP="$PATCH_DIR/lib/dexpatcher-annotation-1.7.0.jar"
[ -n "$ANDROID_JAR" ] && CP="$CP:$ANDROID_JAR"
javac -cp "$CP" -d "$BUILD_DIR/classes" @"$BUILD_DIR/sources.txt"
echo "  ✓ $(wc -l < $BUILD_DIR/sources.txt) sources"

echo "==> Converting to DEX..."
D8=$(find "$SDK/build-tools" -name d8 2>/dev/null | sort -Vr | head -1)
"$D8" --lib "$ANDROID_JAR" --min-api 26 --output "$BUILD_DIR/dex-patch" \
  $(find "$BUILD_DIR/classes" -name "*.class")
echo "  ✓ Patch DEX: $(wc -c < $BUILD_DIR/dex-patch/classes.dex) bytes"

echo "==> apktool decode..."
APKTOOL=$(find /opt -name apktool.jar 2>/dev/null | head -1)
[ -z "$APKTOOL" ] && APKTOOL=$(find "$SDK" -name apktool.jar 2>/dev/null | head -1)
[ -z "$APKTOOL" ] && { echo "  Installing apktool..."; curl -sL "https://github.com/iBotPeaches/Apktool/releases/download/v3.0.2/apktool_3.0.2.jar" -o /opt/apktool.jar; APKTOOL="/opt/apktool.jar"; }

java -jar "$APKTOOL" d "$TARGET_APK" -o "$BUILD_DIR/apktool_out" -f 2>&1 | tail -2
echo "  ✓ Decoded"

echo "==> Patching smali: BottomTabBarItemType.findByValue..."
SMALI_OUT="$BUILD_DIR/apktool_out"
FOUND=0
for sm in $(find "$SMALI_OUT" -name "*BottomTabBarItemType*" 2>/dev/null); do
  if grep -q "findByValue" "$sm"; then
    python3 "$SCRIPT_DIR/patch-smali-findbyvalue.py" "$sm" && FOUND=1
  fi
done
[ $FOUND -eq 0 ] && echo "  ⚠ findByValue smali not found"
echo "  ($FOUND files patched)"

echo "==> Applying DexPatcher patches to dex..."
unzip -q -o "$TARGET_APK" "classes*.dex" -d "$BUILD_DIR/dex-orig"
HIT=0
for dex in "$BUILD_DIR/dex-orig"/classes*.dex; do
  name=$(basename "$dex")
  set +e
  java -jar "$PATCH_DIR/lib/dexpatcher.jar" --verbose -o "$BUILD_DIR/$name.patched" "$dex" "$BUILD_DIR/dex-patch/classes.dex" 2>/dev/null
  RC=$?
  set -e
  if [ $RC -eq 0 ]; then
    sz=$(wc -c < "$BUILD_DIR/$name.patched" 2>/dev/null || echo 0)
    if [ "$sz" -gt 1000 ]; then
      echo "    ✓ $name patched ($sz bytes)"
      cp "$BUILD_DIR/$name.patched" "$SMALI_OUT/$name"
      HIT=1
    fi
  fi
done

echo "==> apktool rebuild..."
cp "$SMALI_OUT/AndroidManifest.xml" "$SMALI_OUT/AndroidManifest.xml.bak"
java -jar "$APKTOOL" b "$SMALI_OUT" -o "$BUILD_DIR/unsigned.apk" 2>&1 | tail -3

# Sign
echo "==> Signing..."
keytool -genkey -v -keystore "$BUILD_DIR/debug.keystore" -alias androiddebugkey \
  -keyalg RSA -keysize 2048 -validity 10000 -storepass android -keypass android \
  -dname "CN=Android Debug, O=Android, C=US" 2>/dev/null
zip -d "$BUILD_DIR/unsigned.apk" 'META-INF/*' 2>/dev/null || true

BT=$(find "$SDK/build-tools" -maxdepth 1 -type d | sort -Vr | head -1)
$BT/zipalign -v -p 4 "$BUILD_DIR/unsigned.apk" "$BUILD_DIR/aligned.apk" 2>&1 | tail -1
$BT/apksigner sign --ks "$BUILD_DIR/debug.keystore" --ks-pass pass:android \
  --ks-key-alias androiddebugkey \
  --out "$OUTPUT_APK" "$BUILD_DIR/aligned.apk" 2>&1 | tail -3
$BT/apksigner verify --verbose "$OUTPUT_APK" 2>&1 | head -5

echo "HIT=$HIT"
ls -lh "$OUTPUT_APK"
