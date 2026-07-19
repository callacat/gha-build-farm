#!/bin/bash
# DexPatcher HelloWorld build script — runs in GHA ubuntu-22.04
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TARGET_APK="${1:?Usage: $0 <target.apk> <sdk-dir> [output.apk]}"
SDK="${2:-/usr/local/lib/android/sdk}"
OUTPUT_APK="${3:-/tmp/hg-dexpatcher-helloworld.apk}"
PATCH_DIR="$SCRIPT_DIR/patches"
BUILD_DIR="/tmp/dexpatcher-build"
HIT=0  # global

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
echo "  ✓ Classes compiled"

# Step 2: DEX
echo "==> Converting to DEX..."
D8=$(find "$SDK/build-tools" -name d8 2>/dev/null | sort -Vr | head -1)
"$D8" --lib "$ANDROID_JAR" --min-api 26 --output "$BUILD_DIR/dex-patch" \
  "$BUILD_DIR/classes/com/dragon/read/MuteApplicationStub.class"
echo "  ✓ Patch DEX: $(wc -c < $BUILD_DIR/dex-patch/classes.dex) bytes"

# Step 3: Extract dex files from APK
echo "==> Extracting dex from APK..."
unzip -q -o "$TARGET_APK" "classes*.dex" -d "$BUILD_DIR/dex-orig"
NUM_DEX=$(ls "$BUILD_DIR/dex-orig"/classes*.dex 2>/dev/null | wc -l)
echo "  Found $NUM_DEX dex files"

# Step 4: Patch each dex
echo "==> Applying DexPatcher patches..."
for dex in "$BUILD_DIR/dex-orig"/classes*.dex; do
  name=$(basename "$dex")
  orig_size=$(wc -c < "$dex")
  echo "  Processing $name ($orig_size bytes)..."
  set +e
  java -jar "$PATCH_DIR/lib/dexpatcher.jar" \
    --verbose \
    -o "$BUILD_DIR/dex-orig/$name.patched" \
    "$dex" \
    "$BUILD_DIR/dex-patch/classes.dex" 2>&1
  RC=$?
  set -e
  echo "    Exit: $RC"
  if [ $RC -eq 0 ]; then
    patched_size=$(wc -c < "$BUILD_DIR/dex-orig/$name.patched")
    # dexpatcher outputs full dex, not just patch fragment
    if [ "$patched_size" -gt 1000 ]; then
      echo "    ✓ $name patched (full dex: $patched_size bytes)"
      mv "$BUILD_DIR/dex-orig/$name.patched" "$dex"
      HIT=1
    fi
  fi
done

# Step 5: Rebuild APK by replacing dex entries using Python zipfile
echo "==> Rebuilding APK with patched dex..."
python3 << PYEOF
import zipfile, os, shutil

BUILD_DIR = "$BUILD_DIR"
TARGET_APK = "$TARGET_APK"
OUTPUT_APK = "$OUTPUT_APK"
DEX_ORIG = os.path.join(BUILD_DIR, "dex-orig")

# Copy original APK
shutil.copy2(TARGET_APK, "$BUILD_DIR/temp.apk")

# Read patched dex files
patched = {}
for f in os.listdir(DEX_ORIG):
    if f.endswith('.dex') and not f.endswith('.patched'):
        fp = os.path.join(DEX_ORIG, f)
        patched[f] = open(fp, 'rb').read()

# Open APK and replace dex entries
with zipfile.ZipFile("$BUILD_DIR/temp.apk", 'r') as zin:
    with zipfile.ZipFile(OUTPUT_APK, 'w', zipfile.ZIP_DEFLATED, compresslevel=0) as zout:
        for item in zin.infolist():
            name = item.filename
            if name in patched:
                print(f"  Replacing {name} ({len(patched[name])} bytes)")
                zout.writestr(item, patched[name])
            else:
                data = zin.read(name)
                zout.writestr(item, data)

print("  ✓ APK rebuilt successfully")
PYEOF

echo "  ✓ Output: $OUTPUT_APK"
ls -lh "$OUTPUT_APK"
python3 -c "
import zipfile
with zipfile.ZipFile('$OUTPUT_APK') as z:
    for n in z.namelist():
        if 'classes' in n:
            print(f'  {n}: {z.getinfo(n).file_size} bytes, is_dir: {n.endswith(\"/\")}')
    print(f'  Total entries: {len(z.namelist())}')
    print(f'  Has AndroidManifest: {\"AndroidManifest.xml\" in z.namelist()}')
"
echo "HIT=$HIT"
