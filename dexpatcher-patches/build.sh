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
mkdir -p "$BUILD_DIR/classes" "$BUILD_DIR/dex-patch" "$BUILD_DIR/dex-orig"

echo "==> Finding android.jar..."
ANDROID_JAR=$(find "$SDK/platforms" -name "android.jar" 2>/dev/null | sort -Vr | head -1)
echo "  android.jar: ${ANDROID_JAR:-NOT FOUND}"

echo "==> Compiling patch..."
CP="$PATCH_DIR/lib/dexpatcher-annotation-1.7.0.jar"
[ -n "$ANDROID_JAR" ] && CP="$CP:$ANDROID_JAR"
find "$PATCH_DIR/src" -name "*.java" -print > "$BUILD_DIR/sources.txt"
javac -cp "$CP" -d "$BUILD_DIR/classes" @"$BUILD_DIR/sources.txt"
echo "  ✓ Classes compiled"

echo "==> Converting to DEX..."
D8=$(find "$SDK/build-tools" -name d8 2>/dev/null | sort -Vr | head -1)
"$D8" --lib "$ANDROID_JAR" --min-api 26 --output "$BUILD_DIR/dex-patch" \
  $(find "$BUILD_DIR/classes" -name "*.class")
echo "  ✓ Patch DEX: $(wc -c < $BUILD_DIR/dex-patch/classes.dex) bytes"

echo "==> Extracting dex from APK..."
unzip -q -o "$TARGET_APK" "classes*.dex" -d "$BUILD_DIR/dex-orig"
NUM_DEX=$(ls "$BUILD_DIR/dex-orig"/classes*.dex 2>/dev/null | wc -l)
echo "  Found $NUM_DEX dex files"

echo "==> Applying DexPatcher patches..."
HIT=0
for dex in "$BUILD_DIR/dex-orig"/classes*.dex; do
  name=$(basename "$dex")
  echo "  Processing $name ($(wc -c < "$dex") bytes)..."
  set +e
  java -jar "$PATCH_DIR/lib/dexpatcher.jar" \
    --verbose \
    -o "$BUILD_DIR/dex-orig/$name.patched" \
    "$dex" \
    "$BUILD_DIR/dex-patch/classes.dex" 2>&1
  RC=$?
  set -e
  if [ $RC -eq 0 ]; then
    patched_size=$(wc -c < "$BUILD_DIR/dex-orig/$name.patched" 2>/dev/null || echo 0)
    if [ "$patched_size" -gt 1000 ]; then
      echo "    ✓ $name patched (full dex: $patched_size bytes)"
      mv "$BUILD_DIR/dex-orig/$name.patched" "$dex"
      HIT=1
    fi
  else
    echo "    - No match in $name, keeping original"
  fi
done

echo "==> Rebuilding APK..."
# Python zipfile rebuild — variables expanded by shell, not os.environ
python3 -c "
import zipfile, os

BUILD_DIR = '$BUILD_DIR'
OUTPUT_APK = '$OUTPUT_APK'
TARGET_APK = '$TARGET_APK'
DEX_ORIG = os.path.join(BUILD_DIR, 'dex-orig')

patched = {}
for f in sorted(os.listdir(DEX_ORIG)):
    if f.endswith('.dex') and not f.endswith('.patched'):
        fp = os.path.join(DEX_ORIG, f)
        patched[f] = open(fp, 'rb').read()

with zipfile.ZipFile(TARGET_APK, 'r') as z:
    entries = []
    seen_names = set()
    for item in z.infolist():
        if item.filename in seen_names:
            continue
        seen_names.add(item.filename)
        try:
            data = z.read(item)
            entries.append((item, data))
        except (zipfile.BadZipFile, KeyError):
            print(f'  (skip overlap: {item.filename})')
            continue

with zipfile.ZipFile(OUTPUT_APK, 'w', zipfile.ZIP_DEFLATED) as zout:
    for item, data in entries:
        name = item.filename
        if name in patched:
            # DEX files must be stored (uncompressed) for Android mmap
            zout.writestr(zipfile.ZipInfo(name), patched[name])
            print(f'  Replaced {name} ({len(patched[name])} bytes)')
        else:
            zout.writestr(item, data)

with zipfile.ZipFile(OUTPUT_APK) as z:
    names = z.namelist()
    dex_count = sum(1 for n in names if n.startswith('classes') and n.endswith('.dex'))
    print(f'  Entries: {len(names)}, dex files: {dex_count}')
    print(f'  Has AndroidManifest: {\"AndroidManifest.xml\" in names}')
    print(f'  Size: {os.path.getsize(OUTPUT_APK)} bytes')
"

echo "HIT=$HIT"
ls -lh "$OUTPUT_APK"
