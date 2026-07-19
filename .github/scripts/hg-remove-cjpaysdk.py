#!/usr/bin/env python3
"""Remove CJPaySDK (com.android.ttcjpaysdk) — 鹿属第三方支付SDK.
Keep com.bytedance.caijing (CJPayFileProvider needed by NewMiraClassloader).
Fix WXPayEntryActivity extends. NOP all CJPaySDK invoke calls + initCaijing().
"""
import re, shutil, sys
from pathlib import Path

APK = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/apktool_out")
TOTAL = 0

# ── Step 1: Delete CJPaySDK only — keep caijing (CJPayFileProvider) ──
print("=== Step 1: Delete CJPaySDK ===")
deleted = 0
for smali_dir in sorted(APK.glob("smali*")):
    if not smali_dir.is_dir(): continue
    t = smali_dir / "com" / "android" / "ttcjpaysdk"
    if t.is_dir():
        c = sum(1 for _ in t.rglob("*.smali"))
        shutil.rmtree(t)
        deleted += c
        print(f"  ✅ {smali_dir.name}/com/android/ttcjpaysdk ({c} files)")
print(f"  → {deleted} files deleted")

# ── Step 2: Fix WXPayEntryActivity extends ──
print("\n=== Step 2: Fix WXPayEntryActivity extends ===")
for f in APK.rglob("*.smali"):
    if "WXPayEntryActivity" in f.name:
        text = f.read_text("utf-8", errors="replace")
        m = re.search(r'\.super L(com/android/ttcjpaysdk/[^;]+);', text)
        if m:
            text = text.replace(m.group(0), '.super Landroid/app/Activity;')
            f.write_text(text, encoding="utf-8")
            TOTAL += 1
            print(f"  ✅ {f.relative_to(APK)}")
        break

# ── Step 3: NOP CJPaySDK invoke calls ──
print("\n=== Step 3: NOP CJPaySDK calls ===")
CJPAY = re.compile(r'invoke-\w+\s+\{[^}]*\},\s*Lcom/android/ttcjpaysdk/[^;]+;->')
CJPAY_CLASS = re.compile(r'const-class\s+[vp]\d+,\s*Lcom/android/ttcjpaysdk/[^;]+;')

for f in sorted(APK.rglob("*.smali")):
    if "/androidx/" in str(f) or "/annotation/" in str(f): continue
    text = f.read_text("utf-8", errors="replace")
    if "com/android/ttcjpaysdk" not in text: continue
    lines = text.splitlines(keepends=True)
    new_lines, i, patched = [], 0, False
    while i < len(lines):
        stripped = lines[i].strip()
        if CJPAY_CLASS.search(stripped) or CJPAY.search(stripped):
            indent = re.match(r"^(\s*)", lines[i]).group(1)
            new_lines.append(f"{indent}nop  # CJPaySDK removed\n")
            patched, TOTAL = True, TOTAL + 1
            print(f"  NOP: {f.relative_to(APK)}:{i+1}")
            i += 1; continue
        if 'com.android.ttcjpaysdk' in stripped:
            indent = re.match(r"^(\s*)", lines[i]).group(1)
            new_lines.append(f"{indent}const-string v0, \"\"  # CJPay removed\n")
            patched, TOTAL = True, TOTAL + 1
            print(f"  STR: {f.relative_to(APK)}:{i+1}")
            i += 1; continue
        new_lines.append(lines[i]); i += 1
    if patched: f.write_text("".join(new_lines), encoding="utf-8")

# ── Step 4: NOP initCaijing() ──
print("\n=== Step 4: NOP initCaijing() ===")
for f in sorted(APK.rglob("*.smali")):
    text = f.read_text("utf-8", errors="replace")
    if "initCaijing" not in text: continue
    lines = text.splitlines(keepends=True)
    new_lines, i, patched = [], 0, False
    while i < len(lines):
        stripped = lines[i].strip()
        if stripped.startswith(".method ") and "initCaijing" in stripped:
            indent = re.match(r"^(\s*)", stripped).group(1)
            j, depth = i + 1, 0
            while j < len(lines):
                s = lines[j].strip()
                if s.startswith(".method "): depth += 1
                elif s.startswith(".end method"):
                    if depth == 0:
                        new_lines.append(f"{indent}.method public static initCaijing(Landroid/content/Context;)V\n")
                        new_lines.append(f"{indent}    .locals 0\n{indent}    return-void  # CJPay removed\n{indent}.end method\n")
                        i, patched, TOTAL = j + 1, True, TOTAL + 1
                        print(f"  ✅ {f.relative_to(APK)}")
                        break
                    depth -= 1
                j += 1
            if not patched: new_lines.append(lines[i]); i += 1
        else: new_lines.append(lines[i]); i += 1
    if patched: f.write_text("".join(new_lines), encoding="utf-8")

print(f"\n=== Complete: {TOTAL} modifications ===")
