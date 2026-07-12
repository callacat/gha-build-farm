#!/usr/bin/env bash
set -euo pipefail

APK_DIR="${1:-/tmp/apktool_out}"

echo "=== 搜索弹窗文本关键词 ==="
grep -rn '立即更新\|温馨提示\|version.*update\|app.*update' "$APK_DIR/res/values"* --include='*.xml' 2>/dev/null | head -30

echo ""
echo "=== 搜索弹窗布局文件 ==="
find "$APK_DIR/res/layout"* -name '*.xml' -exec grep -l 'dialog\|update\|alert' {} \; 2>/dev/null | head -20

echo ""
echo "=== 搜索 smali 中的弹窗调用 ==="
grep -rn 'AlertDialog\|Dialog.*show\|立即更新' "$APK_DIR/smali"* --include='*.smali' 2>/dev/null | grep -v '/androidx/' | head -30

echo ""
echo "=== 搜索网络请求触发点（DNS查询来源） ==="
grep -rn 'HttpURLConnection\|OkHttp\|Retrofit\|URL.*openConnection' "$APK_DIR/smali"* --include='*.smali' 2>/dev/null | grep -v '/androidx/\|/okhttp3/' | head -30
