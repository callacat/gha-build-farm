#!/usr/bin/env bash
set -u
trap "" PIPE

APK_DIR="${1:-/tmp/apktool_out}"
echo "=== 搜索混淆常量池 ==="
grep -rn 'const-string.*"one"\|const-string.*"seeker"\|const-string.*".top"' "$APK_DIR/smali"* --include='*.smali' 2>/dev/null | head -30 || true
echo ""; echo "=== 搜索 StringBuilder.append 拼接 ==="
find "$APK_DIR/smali"* -name '*.smali' -exec grep -l 'StringBuilder' {} \; 2>/dev/null | while read f; do grep -B5 -A5 'append.*".*top"\|append.*".*seek"' "$f" 2>/dev/null | head -20 || true; echo "  文件: $f" || true; done | head -50 || true
echo ""; echo "=== 搜索反射调用 ==="
grep -rn 'Class.*forName\|getDeclaredMethod' "$APK_DIR/smali"* --include='*.smali' 2>/dev/null | grep -i 'update\|version\|check' | head -20 || true
