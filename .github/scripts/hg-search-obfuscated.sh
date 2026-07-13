#!/usr/bin/env bash
set -eu

APK_DIR="${1:-/tmp/apktool_out}"

echo "=== 搜索 ProGuard/R8 混淆后的常量池 ==="
grep -rn 'const-string.*"one"\|const-string.*"seeker"\|const-string.*".top"' "$APK_DIR/smali"* --include='*.smali' 2>/dev/null | head -30 || true

echo ""
echo "=== 搜索字符串拼接模式（StringBuilder.append） ==="
find "$APK_DIR/smali"* -name '*.smali' -exec grep -l 'StringBuilder' {} \; 2>/dev/null | while read f; do
  grep -B5 -A5 'append.*".*top"\|append.*".*seek"' "$f" 2>/dev/null | head -20 || true
  echo "  文件: $f" || true
done | head -50 || true

echo ""
echo "=== 搜索反射调用 Class.forName ==="
grep -rn 'Class.*forName\|getDeclaredMethod' "$APK_DIR/smali"* --include='*.smali' 2>/dev/null | grep -i 'update\|version\|check' | head -20 || true
