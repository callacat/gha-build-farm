#!/usr/bin/env bash
set -u
APK_DIR="${1:-/tmp/apktool_out}"
C=0; MAX=5
show() { [ $C -lt $MAX ] && { echo "$1"; C=$((C+1)); }; }

echo "=== 搜索 .so 可疑字符串 ==="
find "$APK_DIR/lib" -name '*.so' 2>/dev/null | while IFS= read -r so; do
  echo "  $(basename $so)"
  while IFS= read -r L; do show "$L"; done < <(strings "$so" | grep -E 'https?://|\.top|\.com|seeker' 2>/dev/null || true)
done

echo "=== 搜索 JNI update/check ==="
C2=0; MAX2=3
show2() { [ $C2 -lt $MAX2 ] && { echo "$1"; C2=$((C2+1)); }; }
find "$APK_DIR/lib" -name '*.so' 2>/dev/null | while IFS= read -r so; do
  while IFS= read -r L; do show2 "$L"; done < <(nm -D "$so" 2>/dev/null | grep -i 'update\|check\|version' || true)
done

echo "=== 搜索加密字符串特征 ==="
C3=0; MAX3=2
show3() { [ $C3 -lt $MAX3 ] && { echo "$1"; C3=$((C3+1)); }; }
find "$APK_DIR/lib" -name '*.so' 2>/dev/null | while IFS= read -r so; do
  while IFS= read -r L; do show3 "$L"; done < <(strings "$so" | grep -E '^[A-Za-z0-9+/=]{20,}$' 2>/dev/null || true)
done
