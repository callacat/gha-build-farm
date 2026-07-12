#!/usr/bin/env bash
set -euo pipefail

APK_DIR="${1:-/tmp/apktool_out}"

echo "=== 搜索 .so 库中的可疑字符串 ==="
find "$APK_DIR/lib" -name '*.so' 2>/dev/null | while read so; do
  echo "  检查: $(basename $so)"
  # 提取所有 URL 模式
  strings "$so" | grep -E 'https?://|\.top|\.com|seeker' | head -5 || true
done

echo ""
echo "=== 搜索 Native JNI 函数 ==="
find "$APK_DIR/lib" -name '*.so' 2>/dev/null | while read so; do
  # 查找包含 "update" 或 "check" 的导出函数
  nm -D "$so" 2>/dev/null | grep -i 'update\|check\|version' | head -3 || true
done

echo ""
echo "=== 搜索加密字符串特征（base64/hex 长度） ==="
find "$APK_DIR/lib" -name '*.so' 2>/dev/null | while read so; do
  strings "$so" | grep -E '^[A-Za-z0-9+/=]{20,}$' | head -2 || true
done
