#!/usr/bin/env python3
"""NOP 鹿属弹窗：搜所有 smali 中的鹿属类（按内容/文件名），不依赖包路径。
目标类特征：
  - 包含 'C4409'、'C4433'、'DialogFragmentC4433' 等鹿属类名
  - 引用 sgcore0/SafeLoader
  - 位于 classes30.dex（鹿属注入 dex）
"""
import sys, re
from pathlib import Path

APK = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/apktool_out")
TOTAL = 0

# 鹿属类名特征（C44xx 系列的类名编号）
MODDER_CLASSES = ['C4409', 'C441', 'C442', 'C443', 'C444',
                  'DialogFragmentC', 'RunnableC', 'ViewOnClickListenerC',
                  'ViewOnTouchListenerC', 'ViewOnLayoutChangeListenerC']

# 鹿属独有的字面量
MODDER_KEYWORDS = ['sgcore0', 'SafeLoader', 'Hidden0', 'MODE_UPDATE', 'MODE_DECLARATION',
                   'ARG_FORCE_UPDATE', 'ARG_DOWNLOAD_URL', 'ARG_UPDATE_VERSION_NAME']

print("=== Phase 1: 按文件名搜索鹿属类 ===")
for f in sorted(APK.rglob("*.smali")):
    r = str(f.relative_to(APK))
    if any('/androidx/' in r or '/kotlin/' in r for _ in [1]):
        continue
    # 按文件名匹配
    basename = f.stem
    if not any(basename.startswith(cls) for cls in MODDER_CLASSES):
        continue
    text = f.read_text("utf-8", errors="replace")
    lines = text.splitlines(keepends=True)
    modified = False
    i = 0
    count = 0
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
            body_start = i
            i += 1
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
            modified = True
            count += 1
            TOTAL += 1
            i = body_start + len(new_block)
        else:
            i += 1
    if modified:
        f.write_text("".join(lines), encoding="utf-8")
        print(f"  ✅ {r}: {count} methods")

print(f"\n=== Phase 2: 按内容搜索 sgcore0 引用 ===")
for f in sorted(APK.rglob("*.smali")):
    r = str(f.relative_to(APK))
    if any(x in r for x in ['/androidx/', '/kotlin/', '/annotation/']):
        continue
    text = f.read_text("utf-8", errors="replace")
    if not any(kw in text for kw in MODDER_KEYWORDS):
        continue
    # Found sgcore0 reference - stub all methods
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
        print(f"  ✅ {r}: {count} methods (sgcore0)")

print(f"\n=== Total: {TOTAL} methods stubbed ===")
