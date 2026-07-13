#!/usr/bin/env bash
set -u
APK_DIR="${1:-/tmp/apktool_out}"
C=0; MAX=30; show(){ [ $C -lt $MAX ] && { echo "$1"; C=$((C+1)); }; }
echo "=== 搜索混淆常量池 ==="
while IFS= read -r L; do show "$L"; done < <(grep -rn 'const-string.*"one"\|const-string.*"seeker"\|const-string.*".top"' "$APK_DIR/smali"'* --include='"'*.smali" 2>/dev/null || true)
echo ""
echo "=== 搜索 StringBuilder.append 拼接 ==="
C2=0; MAX2=50; show2(){ [ $C2 -lt $MAX2 ] && { echo "$1"; C2=$((C2+1)); }; }
find "$APK_DIR/smali"'* -name '"'*.smali" -exec grep -l 'StringBuilder' {} \; 2>/dev/null | while IFS= read -r f; do
  R=$(grep -B5 -A5 'append.*".*top"\|append.*".*seek"' "$f" 2>/dev/null | head -20 || true)
  [ -n "$R" ] && { echo "$R"; echo "  文件: $f"; } || true
done
echo ""
echo "=== 搜索反射调用 ==="
while IFS= read -r L; do show "$L"; done < <(grep -rn 'Class.*forName\|getDeclaredMethod' "$APK_DIR/smali"'* --include='"'*.smali" 2>/dev/null | grep -i 'update\|version\|check' || true)
