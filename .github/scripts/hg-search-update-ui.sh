#!/usr/bin/env bash
set -u
APK_DIR="${1:-/tmp/apktool_out}"
C=0; MAX=20; show(){ [ $C -lt $MAX ] && { echo "$1"; C=$((C+1)); }; }
echo "=== 搜索 UpdateUI 相关类 ==="
find "$APK_DIR/smali"'* -maxdepth 4 -type d 2>/dev/null | while IFS= read -r d; do
  basename "$d" | grep -qiE '(update|upgrade|version|check)' && echo "$d" || true
done
echo ""
echo "=== 搜索 updateUI/updateView ==="
while IFS= read -r L; do show "$L"; done < <(grep -rn 'updateUI\|updateView\|refreshUI\|refreshView\|invalidate' "$APK_DIR/smali"'* --include='"'*.smali" 2>/dev/null | grep -v 'onRefresh\|SwipeRefreshLayout\|invalidate()Z\|updateUILock' || true)
echo ""
echo "=== 搜索 onResume 中触发更新检测 ==="
find "$APK_DIR/smali"'* -name '"'*.smali" | while IFS= read -r f; do
  grep -q 'onResume' "$f" 2>/dev/null || continue
  ctx=$(grep -A10 'onResume' "$f" 2>/dev/null | grep -iE 'update|check|version|dialog' || true)
  [ -n "$ctx" ] && echo "$f" && echo "$ctx" || true
done
echo ""
echo "=== 搜索 Handler 延时触发 ==="
while IFS= read -r L; do show "$L"; done < <(grep -rn 'sendEmptyMessage\|sendMessageDelayed\|postDelayed\|Handler' "$APK_DIR/smali"'* --include='"'*.smali" 2>/dev/null | grep -iE 'update|check|version' || true)
