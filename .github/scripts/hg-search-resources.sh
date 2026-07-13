#!/usr/bin/env bash
set -u
APK_DIR="${1:-/tmp/apktool_out}"

echo "=== 搜索 resources.arsc 中的 oneseeker ==="
if [ -f "$APK_DIR/resources.arsc" ]; then
  strings "$APK_DIR/resources.arsc" | grep -i oneseeker || echo "  (未找到)"
else
  echo "  resources.arsc 不存在"
fi
echo "=== 搜索 res/ XML ==="
find "$APK_DIR/res" -name '*.xml' 2>/dev/null | xargs grep -Hn 'oneseeker' 2>/dev/null || echo "  (未找到)"
echo "=== 搜索 AndroidManifest meta-data ==="
grep -A2 '<meta-data' "$APK_DIR/AndroidManifest.xml" | grep -i 'update\|version\|check' || echo "  (未找到)"
