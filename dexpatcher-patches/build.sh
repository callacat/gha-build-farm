#!/bin/bash
# DexPatcher build script — javac → d8 → dexpatcher → smali patch → APK rebuild
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

echo "==> Compiling patches..."
find "$PATCH_DIR/src" -name "*.java" -print > "$BUILD_DIR/sources.txt"
CP="$PATCH_DIR/lib/dexpatcher-annotation-1.7.0.jar"
[ -n "$ANDROID_JAR" ] && CP="$CP:$ANDROID_JAR"
javac -cp "$CP" -d "$BUILD_DIR/classes" @"$BUILD_DIR/sources.txt"
echo "  ✓ $(wc -l < $BUILD_DIR/sources.txt) sources compiled"

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
    sz=$(wc -c < "$BUILD_DIR/dex-orig/$name.patched" 2>/dev/null || echo 0)
    if [ "$sz" -gt 1000 ]; then
      echo "    ✓ $name patched ($sz bytes)"
      mv "$BUILD_DIR/dex-orig/$name.patched" "$dex"
      HIT=1
    fi
  else
    echo "    - No match in $name"
  fi
done

# Step: smali patch — modify BottomTabBarItemType.findByValue
echo "==> Applying smali patch to BottomTabBarItemType.findByValue..."
SMALI=$(find "$SDK/build-tools" -name smali 2>/dev/null | sort -Vr | head -1)
BAKSMALI=$(find "$SDK/build-tools" -name baksmali 2>/dev/null | sort -Vr | head -1)

if [ -n "$BAKSMALI" ]; then
  # Find BottomTabBarItemType in the patched dex files
  for dex in "$BUILD_DIR/dex-orig"/classes*.dex; do
    name=$(basename "$dex")
    # Quick check if this dex contains BottomTabBarItemType
    if strings "$dex" | grep -q "BottomTabBarItemType"; then
      echo "  Found BottomTabBarItemType in $name"
      OUTDIR="$BUILD_DIR/baksmali-$name"
      java -jar "$BAKSMALI" d "$dex" -o "$OUTDIR" 2>/dev/null || true
      PATCHED=false
      for smali_file in $(find "$OUTDIR" -name "*BottomTabBarItemType*" 2>/dev/null); do
        if grep -q 'findByValue' "$smali_file"; then
          echo "    Patching findByValue in $(basename $smali_file)..."
          # Insert early return for LuckyBenefit(2) and ShopMall(5)
          python3 -c "
import sys
with open('$smali_file') as f:
    content = f.read()

if '.method public static findByValue' not in content:
    print('    - No findByValue method')
    sys.exit(0)

insert = '''    # filtered by hg-ad-removal: skip ShopMall(5) and LuckyBenefit(2)
    const/4 v0, 0x5
    if-ne p0, v0, :check_lucky
    const/4 v0, 0x0
    return-object v0
    :check_lucky
    const/4 v0, 0x2
    if-ne p0, v0, :original_switch
    const/4 v0, 0x0
    return-object v0
    :original_switch
'''

content = content.replace(
    '.method public static findByValue(I)Lcom/dragon/read/rpc/model/BottomTabBarItemType;',
    '.method public static findByValue(I)Lcom/dragon/read/rpc/model/BottomTabBarItemType;\n' + insert
)
if content != open('$smali_file').read():
    with open('$smali_file', 'w') as f:
        f.write(content)
    print('    ✓ Patched')
    PATCHED = True
else:
    print('    ✗ Match failed')
" 2>&1 || true
      done
      if [ "$PATCHED" = true ]; then
        # Rebuild dex
        java -jar "$SMALI" a "$OUTDIR" -o "$dex" 2>&1 | tail -2
        echo "    ✓ Dex rebuilt"
      fi
      rm -rf "$OUTDIR"
    fi
  done
else
  echo "  baksmali not found, skip smali patch"
fi

echo "==> Rebuilding APK..."
python3 << 'PYEOF'
import zipfile, os

BUILD_DIR = os.environ['BUILD_DIR']
OUTPUT_APK = os.environ['OUTPUT_APK']
TARGET_APK = os.environ['TARGET_APK']
DEX_ORIG = os.path.join(BUILD_DIR, "dex-orig")

patched = {}
for f in sorted(os.listdir(DEX_ORIG)):
    if f.endswith('.dex') and not f.endswith('.patched'):
        fp = os.path.join(DEX_ORIG, f)
        patched[f] = open(fp, 'rb').read()
        print(f"  Replaced {f} ({len(patched[f])} bytes)")

with zipfile.ZipFile(TARGET_APK, 'r') as z:
    entries = []
    seen_names = set()
    for item in z.infolist():
        if item.filename in seen_names: continue
        seen_names.add(item.filename)
        try:
            data = z.read(item)
            entries.append((item, data))
        except: continue

with zipfile.ZipFile(OUTPUT_APK, 'w', zipfile.ZIP_DEFLATED) as zout:
    for item, data in entries:
        name = item.filename
        if name in patched:
            zout.writestr(item, patched[name])
        else:
            zout.writestr(item, data)

with zipfile.ZipFile(OUTPUT_APK) as z:
    names = z.namelist()
    dex_count = sum(1 for n in names if n.startswith('classes') and n.endswith('.dex'))
    print(f"  Entries: {len(names)}, dex files: {dex_count}")
    print(f"  Has AndroidManifest: {'AndroidManifest.xml' in names}")
    print(f"  Size: {os.path.getsize(OUTPUT_APK)} bytes")
PYEOF

echo "HIT=$HIT"
ls -lh "$OUTPUT_APK"
