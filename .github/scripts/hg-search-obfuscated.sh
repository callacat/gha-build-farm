#!/usr/bin/env bash
set -euo pipefail

APK_DIR="${1:-/tmp/apktool_out}"

echo "=== 搜索 ProGuard/R8 混淆后的常量池 ==="
# 混淆后可能把域名拆成 "one" + "seeker" + ".top" 三段存储
grep -rn 'const-string.*"one"\|const-string.*"seeker"\|const-string.*".top"' "$APK_DIR/smali"* --include='*.smali' 2>/dev/null | head -30

echo ""
echo "=== 搜索字符串拼接模式（StringBuilder.append） ==="
# 查找连续的字符串拼接，可能是动态构造域名
find "$APK_DIR/smali"* -name '*.smali' -exec grep -l 'StringBuilder' {} \; | while read f; do
  # 查找包含 "top" 或 "seek" 的 StringBuilder 调用上下文
  grep -B5 -A5 'append.*".*top"\|append.*".*seek"' "$f" 2>/dev/null | head -20 && echo "  文件: $f" || true
done | head -50

echo ""
echo "=== 搜索反射调用 Class.forName ==="
# 可能通过反射动态加载更新类
grep -rn 'Class.*forName\|getDeclaredMethod' "$APK_DIR/smali"* --include='*.smali' 2>/dev/null | grep -i 'update\|version\|check' | head -20
