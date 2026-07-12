#!/usr/bin/env python3
"""红果短剧 v7.2.7.32 — 禁用强制更新弹窗

策略（按优先级）：
1. DialogFragmentC4433.forceUpdate 硬编码为 false
2. 全局 setCancelable(false) → setCancelable(true)
3. 搜索 show() 方法前插入 return-void
"""
import re, sys
from pathlib import Path

APK = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/apktool_out")
MODS = 0
HITS = 0

# ========== 策略 1: 动态搜索 DialogFragment + forceUpdate 字段 ==========
target_class = None
for sd in sorted(APK.glob("smali*")):
    if not sd.is_dir():
        continue
    for f in sd.rglob("*.smali"):
        try:
            t = f.read_text("utf-8", errors="replace")
            # 搜索 DialogFragment 子类 + forceUpdate 字段
            if (re.search(r'\.super.*DialogFragment', t) and
                re.search(r'\.field.*forceUpdate:Z', t)):
                target_class = f
                break
        except:
            continue
    if target_class:
        break

if target_class:
    print(f"✓ 找到目标类: {target_class.relative_to(APK)}")
    t = target_class.read_text("utf-8", errors="replace")
    lines = t.splitlines(keepends=True)
    dirty = False

    for i, ln in enumerate(lines):
        # 匹配 .field private forceUpdate:Z
        if re.search(r'\.field\s+.*forceUpdate:Z', ln):
            print(f"  {target_class.relative_to(APK)}:{i+1}  找到 forceUpdate 字段")
            # 在下一行插入初始化为 false 的逻辑（如果是构造函数）
            # 更简单的方案：搜索所有对 forceUpdate 赋值为 true 的地方，改为 false

        # 匹配 iput-boolean v?, p0, L...;->forceUpdate:Z
        m = re.search(r'iput-boolean\s+(v\d+|p\d+),\s*p0,\s*L[^;]+;->forceUpdate:Z', ln)
        if m:
            reg = m.group(1)
            # 在此行前插入 const/4 vN, 0x0 强制设为 false
            indent = re.match(r'^(\s*)', ln).group(1)
            lines[i] = f'{indent}const/4 {reg}, 0x0  # force forceUpdate=false\n{ln}'
            dirty = True
            HITS += 1
            print(f"  {target_class.relative_to(APK)}:{i+1}  拦截 forceUpdate 赋值")

    if dirty:
        target_class.write_text("".join(lines))
        MODS += 1
else:
    print("⚠ 未找到 DialogFragmentC4433.smali，跳过策略1")

# ========== 策略 2: 全局 setCancelable(false) → setCancelable(true) ==========
print("\n=== 策略2: 修改 setCancelable(false) ===")
for sd in sorted(APK.glob("smali*")):
    if not sd.is_dir():
        continue
    for f in sd.rglob("*.smali"):
        r = str(f.relative_to(APK))
        if "/androidx/" in r or "/annotation/" in r:
            continue

        t = f.read_text("utf-8", errors="replace")
        lines = t.splitlines(keepends=True)
        dirty = False

        for i, ln in enumerate(lines):
            # 匹配 const/4 vN, 0x0 后跟 invoke-virtual {vM, vN}, ...->setCancelable(Z)V
            if 'setCancelable' not in ln:
                continue

            # 向前查找最近的 const/4 vX, 0x0（false）
            for j in range(max(0, i-5), i):
                prev = lines[j]
                m = re.search(r'const/4\s+(v\d+),\s*0x0', prev)
                if m and m.group(1) in ln:
                    # 找到对应的 false 常量，修改为 0x1
                    reg = m.group(1)
                    indent = re.match(r'^(\s*)', prev).group(1)
                    lines[j] = f'{indent}const/4 {reg}, 0x1  # patch: setCancelable(true)\n'
                    dirty = True
                    HITS += 1
                    print(f"  {f.relative_to(APK)}:{j+1}  setCancelable(false)→true")
                    break

        if dirty:
            f.write_text("".join(lines))
            MODS += 1

# ========== 策略 3: 兜底 - 搜索 show() 方法前插入 return-void（高风险，暂不启用）==========
# 此策略会导致所有 Dialog 无法显示，暂时注释
# print("\n=== 策略3: show() 方法短路（已禁用）===")

print(f"\n=== 补丁完成: {MODS} 个文件修改, {HITS} 处拦截 ===")
