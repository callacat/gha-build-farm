#!/usr/bin/env bash
set -euo pipefail

APK_DIR="${1:-/tmp/apktool_out}"

echo "=== 全量搜索 oneseeker 引用 ==="
echo ""

echo "1. AndroidManifest.xml"
grep -n 'oneseeker' "$APK_DIR/AndroidManifest.xml" || echo "  (未找到)"
echo ""

echo "2. res/values/strings.xml"
find "$APK_DIR/res/values"* -name '*.xml' -exec grep -Hn 'oneseeker' {} \; || echo "  (未找到)"
echo ""

echo "3. assets/ 配置文件"
find "$APK_DIR/assets" -type f -exec grep -Hn 'oneseeker' {} \; 2>/dev/null || echo "  (未找到)"
echo ""

echo "4. Native .so 库"
find "$APK_DIR/lib" -name '*.so' -exec sh -c 'strings "$1" | grep -qi oneseeker && echo "  $1: FOUND"' _ {} \; || echo "  (未找到)"
echo ""

echo "5. Smali 分段拼接（seeker关键词）"
grep -rn 'seeker' "$APK_DIR/smali"* --include='*.smali' | grep -v 'oneseeker.top' | head -20 || echo "  (未找到)"
echo ""

echo "6. Base64 编码（b25lc2Vla2VyLnRvcA==）"
grep -rn 'b25lc2Vla2VyLnRvcA==' "$APK_DIR" || echo "  (未找到)"
echo ""

echo "7. 十六进制编码"
grep -rn '6f6e657365656b65722e746f70' "$APK_DIR/smali"* --include='*.smali' || echo "  (未找到)"
echo ""

echo "=== 搜索完成 ==="
