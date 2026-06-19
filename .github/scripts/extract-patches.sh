#!/usr/bin/env bash
set -euo pipefail

mkdir -p patches

# 1. Manifest: appComponentFactory
grep -n 'appComponentFactory' official_smali/AndroidManifest.xml > patches/manifest-official.txt
grep -n 'appComponentFactory' modded_smali/AndroidManifest.xml > patches/manifest-modded.txt
echo "Official: $(cat patches/manifest-official.txt)"
echo "Modded:  $(cat patches/manifest-modded.txt)"

# 2. Lancet getPackageInfo hooks
for f in zo4/b.smali uo4/l.smali; do
  found=$(find modded_smali -path "smali*/$f" 2>/dev/null | head -1)
  if [ -n "$found" ]; then
    dest="patches/$(echo "$found" | sed 's|modded_smali/||')"
    mkdir -p "$(dirname "$dest")"
    cp "$found" "$dest"
    echo "Lancet hook: $found"
  fi
done

# 3. DPatch framework files
find modded_smali -path "*/pandora/core/*" -name "*.smali" 2>/dev/null > /tmp/dpatch.list
while IFS= read -r f; do
  dest="patches/dpatch/$(echo "$f" | sed 's|modded_smali/||')"
  mkdir -p "$(dirname "$dest")"
  cp "$f" "$dest"
done < /tmp/dpatch.list
echo "DPatch files: $(wc -l < /tmp/dpatch.list)"

# 4. Lancet declarations
grep -rn 'Lancet\|@Proxy\|@BaseProxy\|@ProxyField' modded_smali/smali*/ --include='*.smali' 2>/dev/null \
  | grep -v '\.\.\/' > patches/lancet-declarations.txt
echo "Lancet declarations: $(wc -l < patches/lancet-declarations.txt)"

# 5. Also grab the official versions of modified files for diff
find modded_smali -path "*/pandora/core/*" -name "*.smali" > /tmp/dpatch.list
while IFS= read -r f; do
  off_f="${f/modded_smali/official_smali}"
  if [ -f "$off_f" ]; then
    dest="patches/official-dpatch/$(echo "$off_f" | sed 's|official_smali/||')"
    mkdir -p "$(dirname "$dest")"
    cp "$off_f" "$dest"
  fi
done < /tmp/dpatch.list
