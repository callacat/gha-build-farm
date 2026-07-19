#!/usr/bin/env python3
"""NOP 鹿属弹窗：打桩 DialogFragmentC4433 + sgcore0 所有方法
这些是鹿属注入的纯弹窗/后门类，不存在官方依赖。
"""
import sys, re
from pathlib import Path

APK = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/apktool_out")
TOTAL = 0

TARGET_PACKAGES = [
    "org/checkerframework/checker/signature/query/security",
    "sgcore0",
]

for pkg in TARGET_PACKAGES:
    found = False
    for smali_dir in sorted(APK.glob("smali*")):
        pkg_dir = smali_dir / pkg
        if not pkg_dir.is_dir():
            continue
        found = True
        for f in sorted(pkg_dir.rglob("*.smali")):
            text = f.read_text("utf-8", errors="replace")
            lines = text.splitlines(keepends=True)
            modified = False
            i = 0
            while i < len(lines):
                ln = lines[i]
                m = re.match(r'^(\s*)\.method\s', ln)
                if m:
                    indent = m.group(1)
                    # Collect method body
                    body_start = i
                    i += 1
                    while i < len(lines) and not re.match(r'^\s*\.end\s+method', lines[i]):
                        i += 1
                    method_end = i
                    sig = lines[body_start].strip()
                    # Skip abstract/native/constructor
                    if 'abstract' in sig or 'native' in sig:
                        i += 1
                        continue
                    if '<init>' in sig or '<clinit>' in sig:
                        i += 1
                        continue
                    # Extract return type
                    idx = sig.rfind(')')
                    ret = sig[idx+1:] if idx >= 0 else ''
                    # Determine stub
                    if ret == 'V':
                        stub = [f'{indent}.locals 0\n', f'{indent}return-void\n']
                    elif ret == 'Z' or ret == 'I' or ret == 'F' or ret == 'B' or ret == 'S' or ret == 'C':
                        stub = [f'{indent}.locals 1\n', f'{indent}const/4 v0, 0x0\n', f'{indent}return v0\n']
                    elif ret == 'J' or ret == 'D':
                        stub = [f'{indent}.locals 2\n', f'{indent}const-wide/16 v0, 0x0\n', f'{indent}return-wide v0\n']
                    elif ret.startswith('L') or ret.startswith('['):
                        stub = [f'{indent}.locals 1\n', f'{indent}const/4 v0, 0x0\n', f'{indent}return-object v0\n']
                    else:
                        i += 1
                        continue
                    # Replace body with stub
                    new_block = [lines[body_start]] + stub + [lines[method_end]]
                    lines[body_start:method_end+1] = new_block
                    modified = True
                    TOTAL += 1
                    if TOTAL <= 15:
                        rel = str(f.relative_to(APK))
                        print(f"  ✅ {rel}: {sig.split('(')[0].split()[-1][:50]}")
                    i = body_start + len(new_block)
                else:
                    i += 1
            if modified:
                f.write_text("".join(lines), encoding="utf-8")
    if not found:
        print(f"  📁 {pkg}: 目录不存在，跳过")

print(f"\n=== Total: {TOTAL} methods stubbed ===")
