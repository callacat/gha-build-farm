#!/usr/bin/env python3
"""Remove CJPaySDK (com.android.ttcjpaysdk) safely.

Strategy:
1. Delete CJPaySDK smali directories (1684 files)
2. Fix WXPayEntryActivity: change .super from CJPaySDK to Activity
3. Find all smali files that invoke CJPaySDK methods and replace with nop+pop
4. Clean Manifest + string references

For smali: invoke-* calls have the pattern:
  invoke-{kind} {regs}, Lpackage/Class;->method(params)return
To NOP safely: replace with pop/pop (clear stack) + nop
For void methods: just nop the invoke
For non-void: need to handle return value (add: const/4 v0, 0x0 after)
"""
import re, shutil, sys
from pathlib import Path

APK = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/apktool_out")
TOTAL = 0

# ── Step 1: Delete CJPaySDK ──
print("=== Step 1: Delete CJPaySDK smali ===")
deleted = 0
for smali_dir in sorted(APK.glob("smali*")):
    if not smali_dir.is_dir(): continue
    t = smali_dir / "com" / "android" / "ttcjpaysdk"
    if t.is_dir():
        c = sum(1 for _ in t.rglob("*.smali"))
        shutil.rmtree(t)
        deleted += c
        print(f"  ✅ {smali_dir.name}/com/android/ttcjpaysdk ({c} files)")
# Also delete caijing SDK
for smali_dir in sorted(APK.glob("smali*")):
    if not smali_dir.is_dir(): continue
    t = smali_dir / "com" / "bytedance" / "caijing"
    if t.is_dir():
        c = sum(1 for _ in t.rglob("*.smali"))
        shutil.rmtree(t)
        deleted += c
        print(f"  ✅ {smali_dir.name}/com/bytedance/caijing ({c} files)")
print(f"  → {deleted} files deleted")

# ── Step 2: Fix WXPayEntryActivity ──
print("\n=== Step 2: Fix WXPayEntryActivity extends ===")
for f in APK.rglob("*.smali"):
    if "WXPayEntryActivity" in f.stem:
        text = f.read_text("utf-8", errors="replace")
        m = re.search(r'\.super L(com/android/ttcjpaysdk/[^;]+);', text)
        if m:
            text = text.replace(m.group(0), '.super Landroid/app/Activity;')
            f.write_text(text, encoding="utf-8")
            TOTAL += 1
            print(f"  ✅ {f.relative_to(APK)}")
        break

# ── Step 3: NOP CJPaySDK invoke calls in app smali ──
print("\n=== Step 3: NOP CJPaySDK invoke calls + initCaijing() ===")
CJPAY_INVOKE = re.compile(r'invoke-\w+\s+\{[^}]*\},\s*L(?:com/android/ttcjpaysdk/|com/bytedance/caijing/)[^;]+;->')
CONST_CLASS = re.compile(r'const-class\s+[vp]\d+,\s*L(?:com/android/ttcjpaysdk/|com/bytedance/caijing/)[^;]+;')

for f in sorted(APK.rglob("*.smali")):
    if "/androidx/" in str(f) or "/annotation/" in str(f):
        continue
    text = f.read_text("utf-8", errors="replace")
    if "com/android/ttcjpaysdk" not in text and "com/bytedance/caijing" not in text:
        continue
    lines = text.splitlines(keepends=True)
    new_lines = []
    i, patched = 0, False
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        # NOP const-class references
        if CONST_CLASS.search(stripped):
            indent = re.match(r"^(\s*)", line).group(1)
            new_lines.append(f"{indent}nop  # CJPaySDK removed\n")
            TOTAL += 1; patched = True
            print(f"  NOP const-class: {f.relative_to(APK)}:{i+1}")
            i += 1
            continue
        # NOP invoke calls
        if CJPAY_INVOKE.search(stripped):
            indent = re.match(r"^(\s*)", line).group(1)
            new_lines.append(f"{indent}nop  # CJPaySDK removed\n")
            TOTAL += 1; patched = True
            print(f"  NOP invoke: {f.relative_to(APK)}:{i+1}")
            i += 1
            continue
        # Comment out lines referencing CJPaySDK in string form
        # These are in string arrays or class name strings
        if ('com.android.ttcjpaysdk' in stripped or 'com.bytedance.caijing' in stripped) and 'const-string' in stripped:
            indent = re.match(r"^(\s*)", line).group(1)
            new_lines.append(f"{indent}const-string v0, \"\"  # CJPaySDK removed\n")
            TOTAL += 1; patched = True
            print(f"  Clear string: {f.relative_to(APK)}:{i+1}")
            i += 1
            continue
        # Comment out array-element references
        if 'com.android.ttcjpaysdk' in stripped or 'com.bytedance.caijing' in stripped:
            indent = re.match(r"^(\s*)", line).group(1)
            # Try to replace with empty string reference
            new_lines.append(f"{indent}nop  # CJPaySDK removed\n")
            TOTAL += 1; patched = True
            print(f"  NOP ref: {f.relative_to(APK)}:{i+1}")
            i += 1
            continue
        new_lines.append(line)
        i += 1
    if patched:
        f.write_text("".join(new_lines), encoding="utf-8")

# ── Step 3b: NOP initCaijing() method in NsCaijingProxy ──
print("\n=== Step 3b: NOP initCaijing() ===")
for f in sorted(APK.rglob("*.smali")):
    text = f.read_text("utf-8", errors="replace")
    if "initCaijing" not in text:
        continue
    lines = text.splitlines(keepends=True)
    new_lines = []
    i, patched = 0, False
    while i < len(lines):
        stripped = lines[i].strip()
        if stripped.startswith(".method ") and "initCaijing" in stripped:
            indent = re.match(r"^(\s*)", lines[i]).group(1)
            # Find .end method
            j = i + 1
            depth = 0
            while j < len(lines):
                s = lines[j].strip()
                if s.startswith(".method "): depth += 1
                elif s.startswith(".end method"):
                    if depth == 0:
                        new_lines.append(f"{indent}.method public static initCaijing(Landroid/content/Context;)V\n")
                        new_lines.append(f"{indent}    .locals 0\n")
                        new_lines.append(f"{indent}    return-void  # CJPaySDK removed\n")
                        new_lines.append(f"{indent}.end method\n")
                        i = j + 1
                        patched = True
                        TOTAL += 1
                        print(f"  ✅ {f.relative_to(APK)}: initCaijing NOP'd")
                        break
                    depth -= 1
                j += 1
            if not patched: new_lines.append(lines[i]); i += 1
        else:
            new_lines.append(lines[i]); i += 1
    if patched:
        f.write_text("".join(new_lines), encoding="utf-8")

# ── Step 4: Clean Manifest ──
print("\n=== Step 4: Clean Manifest ===")
manifest = APK / "AndroidManifest.xml"
if manifest.exists():
    text = manifest.read_text("utf-8", errors="replace")
    text = re.sub(r'<uses-permission android:name="[^"]*cjpay[^"]*"/>\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'<permission[^>]*cjpay[^"]*"[^>]*/>\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'android:label="CJPay[^"]*"', '', text)
    # Match both self-closing AND multi-line component declarations
    for comp in ['activity', 'service', 'receiver', 'provider']:
        text = re.sub(r'(<' + comp + r'\s+[^>]*?(?:ttcjpaysdk|caijing)[^>]*/?>)',
                      r'<!-- CJPay removed: \1 -->', text, flags=re.DOTALL)
        # Also match block tags with children (like provider with meta-data)
        text = re.sub(r'(<' + comp + r'\s+(?:[^>]*?(?:ttcjpaysdk|caijing)[^>]*?>[^<]*</' + comp + r'>))',
                      r'<!-- CJPay removed: \1 -->', text, flags=re.DOTALL)
    manifest.write_text(text, encoding="utf-8")
    print(f"  ✅ Manifest cleaned")

print(f"\n=== Complete: {TOTAL} modifications ===")
