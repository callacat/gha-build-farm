#!/usr/bin/env bash
# hg-nop-modder.sh — Find and NOP the method containing "oneseeker.top"
set -euo pipefail
APK_DIR="${1:-/tmp/apktool_out}"

# Search for oneseeker.top in all smali files
FILE=$(grep -rl "oneseeker.top" "$APK_DIR/smali"* 2>/dev/null | head -1)
if [ -z "$FILE" ]; then
  echo "[SKIP] oneseeker.top not found"
  exit 0
fi

echo "=== Found: $FILE ==="

# Find the method containing it + get return type
# Get the method signature above the URL line
URL_LINE=$(grep -n "oneseeker.top" "$FILE" | head -1 | cut -d: -f1)
METHOD_LINE=""
for i in $(seq $URL_LINE -1 1); do
  LINE=$(sed -n "${i}p" "$FILE")
  if echo "$LINE" | grep -q "\.method "; then
    METHOD_LINE=$i
    # Extract return type: last char inside the descriptor after last paren
    DESCR=$(echo "$LINE" | grep -oP '\)[A-Z]' | head -1 | cut -c2)
    [ -z "$DESCR" ] && DESCR="V"
    echo "  Method at line $METHOD_LINE return=$DESCR"
    break
  fi
done

# Find the .end method line
END_LINE=""
for i in $(seq $URL_LINE 1 $((URL_LINE + 200))); do
  LINE=$(sed -n "${i}p" "$FILE" 2>/dev/null)
  [ -z "$LINE" ] && break
  if echo "$LINE" | grep -q "\.end method"; then
    END_LINE=$i
    break
  fi
done

if [ -z "$METHOD_LINE" ] || [ -z "$END_LINE" ]; then
  echo "[FAIL] Could not find method boundaries"
  exit 1
fi

echo "  Method spans lines $METHOD_LINE-$END_LINE"

# NOP: keep method sig, replace body with minimal return
{
  sed -n "1,${METHOD_LINE}p" "$FILE"
  echo "    .locals 0"
  if [ "$DESCR" = "V" ]; then
    echo "    return-void  # disabled"
  else
    echo "    const/4 v0, 0x0"
    echo "    return v0  # disabled (false/0/null)"
  fi
  echo ".end method"
  sed -n "$((END_LINE + 1)),\$p" "$FILE"
} > "$FILE.tmp" && mv "$FILE.tmp" "$FILE"

echo "  ✅ NOPped (return=$( [ "$DESCR" = "V" ] && echo "void" || echo "value" ))"
echo "=== Done ==="
