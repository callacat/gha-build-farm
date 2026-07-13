#!/usr/bin/env bash
# 内部计数器限制行数，零 | head 管道风险
set -u
APK_DIR="${1:-/tmp/apktool_out}"
C=0; MAX=30
show() { [ $C -lt $MAX ] && { echo "$1"; C=$((C+1)); }; }

echo "=== 全量搜索 oneseeker 引用 ==="
echo "1. AndroidManifest.xml"
grep -n 'oneseeker' "$APK_DIR/AndroidManifest.xml" || echo "  (未找到)"
echo "2. res/values/strings.xml"
find "$APK_DIR/res/values"* -name '*.xml' -exec grep -Hn 'oneseeker' {} \; || echo "  (未找到)"
echo "3. assets/"
find "$APK_DIR/assets" -type f -exec grep -Hn 'oneseeker' {} \; 2>/dev/null || echo "  (未找到)"
echo "4. Native .so"
find "$APK_DIR/lib" -name '*.so' -exec sh -c 'strings "$1" | grep -qi oneseeker && echo "  $1: FOUND"' _ {} \; || echo "  (未找到)"
echo "5. Smali seeker"
while IFS= read -r L; do show "$L"; done < <(grep -rn 'seeker' "$APK_DIR/smali"* --include='*.smali' 2>/dev/null | grep -v 'oneseeker.top' || true)
echo "6. Base64"
grep -rn 'b25lc2Vla2VyLnRvcA==' "$APK_DIR" || echo "  (未找到)"
echo "7. Hex"
grep -rn '6f6e657365656b65722e746f70' "$APK_DIR/smali"* --include='*.smali' 2>/dev/null || echo "  (未找到)"
echo "=== Done ==="
