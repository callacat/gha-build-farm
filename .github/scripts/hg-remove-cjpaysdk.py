#!/usr/bin/env python3
"""Remove CJPaySDK — keep Manifest provider but delete all smali + NOP calls.
Manifest is untouched to avoid XML corruption. CJPayFileProvider will survive
because we keep a stub reference (empty class) if needed.
"""
import re, shutil, sys
from pathlib import Path

APK = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/apktool_out")
TOTAL = 0

def nop_method(f, method_name):
    """NOP an entire method body by name."""
    global TOTAL
    text = f.read_text("utf-8", errors="replace")
    if method_name not in text.splitlines()[0 if not text else 0]:
        pass
    lines = text.splitlines(keepends=True)
    new_lines, i, patched = [], 0, False
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if stripped.startswith(".method ") and method_name in stripped:
            indent = re.match(r"^(\s*)", line).group(1)
            j, depth = i + 1, 0
            while j < len(lines):
                s = lines[j].strip()
                if s.startswith(".method "): depth += 1
                elif s.startswith(".end method"):
                    if depth == 0:
                        new_lines.append(f"{indent}.method public static {method_name}(Landroid/content/Context;)V\n")
                        new_lines.append(f"{indent}    .locals 0\n")
                        new_lines.append(f"{indent}    return-void  # CJPay removed\n")
                        new_lines.append(f"{indent}.end method\n")
                        i = j + 1
                        patched, TOTAL = True, TOTAL + 1
                        print(f"  ✅ {f.relative_to(APK)}: {method_name} NOP'd")
                        break
                    depth -= 1
                j += 1
            if not patched: new_lines.append(line); i += 1
        else:
            new_lines.append(line); i += 1
    if patched:
        f.write_text("".join(new_lines), encoding="utf-8")
    return patched

# ── Step 1: Delete CJPaySDK smali ──
print("=== Step 1: Delete CJPaySDK ===")
deleted = 0
for smali_dir in sorted(APK.glob("smali*")):
    if not smali_dir.is_dir(): continue
    for pkg in ["com/android/ttcjpaysdk", "com/bytedance/caijing"]:
        t = smali_dir / pkg
        if t.is_dir():
            c = sum(1 for _ in t.rglob("*.smali"))
            shutil.rmtree(t)
            deleted += c
            print(f"  ✅ {smali_dir.name}/{pkg} ({c} files)")
print(f"  → {deleted} files deleted")

# ── Step 1b: Create stub CJPayFileProvider to prevent Manifest crash ──
print("\n=== Step 1b: Create stub CJPayFileProvider ===")
stub = """\
.class public Lcom/bytedance/caijing/sdk/infra/base/api/plugin/provider/CJPayFileProvider;
.super Landroid/content/ContentProvider;
.source "CJPayFileProvider.java"

.method public constructor <init>()V
    .locals 0
    invoke-direct {p0}, Landroid/content/ContentProvider;-><init>()V
    return-void
.end method

.method public delete(Landroid/net/Uri;Ljava/lang/String;[Ljava/lang/String;)I
    .locals 0
    const/4 v0, 0x0
    return v0
.end method

.method public getType(Landroid/net/Uri;)Ljava/lang/String;
    .locals 0
    const/4 v0, 0x0
    return-object v0
.end method

.method public insert(Landroid/net/Uri;Landroid/content/ContentValues;)Landroid/net/Uri;
    .locals 0
    const/4 v0, 0x0
    return-object v0
.end method

.method public onCreate()Z
    .locals 0
    const/4 v0, 0x1
    return v0
.end method

.method public query(Landroid/net/Uri;[Ljava/lang/String;Ljava/lang/String;[Ljava/lang/String;Ljava/lang/String;)Landroid/database/Cursor;
    .locals 0
    const/4 v0, 0x0
    return-object v0
.end method

.method public update(Landroid/net/Uri;Landroid/content/ContentValues;Ljava/lang/String;[Ljava/lang/String;)I
    .locals 0
    const/4 v0, 0x0
    return v0
.end method
"""

# Put stub in the first smali dir that has any CJPay file
for smali_dir in sorted(APK.glob("smali*")):
    if not smali_dir.is_dir(): continue
    target = smali_dir / "com" / "bytedance" / "caijing" / "sdk" / "infra" / "base" / "api" / "plugin" / "provider"
    target.mkdir(parents=True, exist_ok=True)
    (target / "CJPayFileProvider.smali").write_text(stub, encoding="utf-8")
    print(f"  ✅ Stub created: {target}/CJPayFileProvider.smali")
    TOTAL += 1
    break

# ── Step 2: Fix WXPayEntryActivity extends ──
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

# ── Step 3: NOP invokes, const-class, string refs ──
print("\n=== Step 3: NOP CJPay invoke calls ===")
CJPAY = re.compile(r'invoke-\w+\s+\{[^}]*\},\s*L(?:com/android/ttcjpaysdk/|com/bytedance/caijing/)[^;]+;->')
CONST = re.compile(r'const-class\s+[vp]\d+,\s*L(?:com/android/ttcjpaysdk/|com/bytedance/caijing/)[^;]+;')

for f in sorted(APK.rglob("*.smali")):
    if "/androidx/" in str(f) or "/annotation/" in str(f): continue
    text = f.read_text("utf-8", errors="replace")
    if "com/android/ttcjpaysdk" not in text and "com/bytedance/caijing" not in text: continue
    lines = text.splitlines(keepends=True)
    new_lines, i, patched = [], 0, False
    while i < len(lines):
        line, stripped = lines[i], lines[i].strip()
        if CONST.search(stripped):
            indent = re.match(r"^(\s*)", line).group(1)
            new_lines.append(f"{indent}nop  # CJPay\n"); patched = True; TOTAL += 1
            print(f"  const-class: {f.relative_to(APK)}:{i+1}")
            i += 1; continue
        if CJPAY.search(stripped):
            indent = re.match(r"^(\s*)", line).group(1)
            new_lines.append(f"{indent}nop  # CJPay\n"); patched = True; TOTAL += 1
            print(f"  invoke: {f.relative_to(APK)}:{i+1}")
            i += 1; continue
        if ('com.android.ttcjpaysdk' in stripped or 'com.bytedance.caijing' in stripped):
            indent = re.match(r"^(\s*)", line).group(1)
            new_lines.append(f"{indent}const-string v0, \"\"  # CJPay removed\n")
            patched = True; TOTAL += 1
            print(f"  string: {f.relative_to(APK)}:{i+1}")
            i += 1; continue
        new_lines.append(line); i += 1
    if patched:
        f.write_text("".join(new_lines), encoding="utf-8")

# ── Step 4: NOP initCaijing ──
print("\n=== Step 4: NOP initCaijing() ===")
for f in sorted(APK.rglob("*.smali")):
    if nop_method(f, "initCaijing"): break

print(f"\n=== Complete: {TOTAL} modifications ===")
