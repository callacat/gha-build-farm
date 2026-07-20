#!/usr/bin/env python3
"""NOP 鹿属弹窗：全局搜 smali 中的 Lsgcore0/ 引用，找到鹿属注入类并全部打桩。

鹿属把类注入到 classes30.dex，R8 混淆后文件名为 unicode 单字符
（如 а.smali），内容中引用 Lsgcore0/SafeLoader;，这是唯一稳定特征。
"""
import sys, re
from pathlib import Path

APK = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/apktool_out")
TOTAL = 0

print("=== 搜索所有引用 sgcore0/SafeLoader 的 smali 文件 ===")
for f in sorted(APK.rglob("*.smali")):
    r = str(f.relative_to(APK))
    text = f.read_text("utf-8", errors="replace")
    if 'Lsgcore0/' not in text and 'sgcore0' not in text:
        continue

    # Found a modder class — stub ALL methods
    lines = text.splitlines(keepends=True)
    modified = False
    count = 0
    i = 0
    while i < len(lines):
        ln = lines[i]
        m = re.match(r'^(\s*)\.method\s', ln)
        if m:
            indent = m.group(1)
            sig = ln.strip()
            if 'abstract' in sig or 'native' in sig:
                i += 1; continue
            if '<init>' in sig or '<clinit>' in sig:
                i += 1; continue
            body_start = i; i += 1
            while i < len(lines) and not re.match(r'^\s*\.end\s+method', lines[i]):
                i += 1
            method_end = i
            idx = sig.rfind(')')
            ret = sig[idx+1:] if idx >= 0 else ''
            if ret == 'V':
                stub = [f'{indent}.locals 0\n', f'{indent}return-void\n']
            elif ret in ('Z','I','F','B','S','C'):
                stub = [f'{indent}.locals 1\n', f'{indent}const/4 v0, 0x0\n', f'{indent}return v0\n']
            elif ret in ('J','D'):
                stub = [f'{indent}.locals 2\n', f'{indent}const-wide/16 v0, 0x0\n', f'{indent}return-wide v0\n']
            elif ret.startswith('L') or ret.startswith('['):
                stub = [f'{indent}.locals 1\n', f'{indent}const/4 v0, 0x0\n', f'{indent}return-object v0\n']
            else:
                i += 1; continue
            new_block = [lines[body_start]] + stub + [lines[method_end]]
            lines[body_start:method_end+1] = new_block
            modified = True; count += 1; TOTAL += 1
            i = body_start + len(new_block)
        else:
            i += 1
    if modified:
        f.write_text("".join(lines), encoding="utf-8")
        print(f"  ✅ {r}: {count} methods")

print(f"\n=== Total: {TOTAL} methods stubbed ===")
