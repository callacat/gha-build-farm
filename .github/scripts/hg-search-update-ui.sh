#!/usr/bin/env bash
set -eu

APK_DIR="${1:-/tmp/apktool_out}"

echo "=== 搜索 UpdateUI 相关类 ==="
find "$APK_DIR/smali"* -maxdepth 4 -type d 2>/dev/null | while read d; do
  basename "$d" | grep -qiE '(update|upgrade|version|check)' && echo "$d" || true
done | head -20 || true

echo ""
echo "=== 搜索 updateUI / updateView ==="
grep -rn 'updateUI\|updateView\|refreshUI\|refreshView\|invalidate' "$APK_DIR/smali"* --include='*.smali' 2>/dev/null | grep -v 'onRefresh\|SwipeRefreshLayout\|invalidate()Z\|updateUILock' | head -30 || true

echo ""
echo "=== 搜索 onResume 中启动更新检测 ==="
find "$APK_DIR/smali"* -name '*.smali' | while read f; do
  grep -q 'onResume' "$f" 2>/dev/null || continue
  ctx=$(grep -A10 'onResume' "$f" 2>/dev/null | grep -iE 'update|check|version|dialog' || true)
  [ -n "$ctx" ] && echo "$f" && echo "$ctx" || true
done | head -30 || true

echo ""
echo "=== 搜索 Handler/Thread 延时触发更新 ==="
grep -rn 'sendEmptyMessage\|sendMessageDelayed\|postDelayed\|Handler' "$APK_DIR/smali"* --include='*.smali' 2>/dev/null | grep -iE 'update|check|version' | head -20 || true
