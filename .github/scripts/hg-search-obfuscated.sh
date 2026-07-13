#!/usr/bin/env bash
# hg-search-obfuscated.sh — 内部计数器限制输出行数，零管道风险
set -u
APK_DIR="${1:-/tmp/apktool_out}"
C=0; MAX=30
show() { [ $C -lt $MAX ] && { echo "$1"; C=$((C+1)); }; }

echo "=== 搜索混淆常量池 ==="
while IFS= read -r L; do show "$L"; done < <(
  grep -rn 'const-string.*"one"\|const-string.*"seeker"\|const-string.*".top"' \
    "$APK_DIR/smali"* --include='*.smali' 2>/dev/null || true
)

echo ""
echo "=== 搜索 StringBuilder.append 拼接 ==="
find "$APK_DIR/smali"* -name '*.smali' -exec grep -l 'StringBuilder' {} \; 2>/dev/null | \
while IFS= read -r f; do
  R=$(grep -B5 -A5 'append.*".*top"\|append.*".*seek"' "$f" 2>/dev/null)
  [ -n "$R" ] && { echo "$R"; echo "  文件: $f"; }
done

echo ""
echo "=== 搜索反射调用 ==="
while IFS= read -r L; do show "$L"; done < <(
  grep -rn 'Class.*forName\|getDeclaredMethod' "$APK_DIR/smali"* --include='*.smali' 2>/dev/null \
    | grep -i 'update\|version\|check' || true
)
