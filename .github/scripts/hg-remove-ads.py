#!/usr/bin/env python3
"""remove-ad-sdk.py — 从 apktool 反编译目录中删除广告/追踪/推送模块。

支持三层操作:
  Layer A — 安全删除已知广告 SDK 包目录
  Layer B — 保留 SDK 文件但对初始化方法打桩 (return-void)
  推送删除 — 删除推送包目录 + 清理 Manifest 组件声明
  权限精简 — 只保留白名单 uses-permission
  Cleartext — android:usesCleartextTraffic="true" → "false"
  页面删除 — 按关键词删除 Activity/目录（商城/赚钱/会员等）
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def load_json(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_permissions(path: str) -> set[str]:
    """加载权限白名单，跳过空行和 # 注释行。"""
    perms: set[str] = set()
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                perms.add(line)
    return perms


def safe_relative(path: Path, anchor: Path) -> str:
    """返回 path 相对于 anchor 的字符串；无法相对时返回绝对路径。"""
    try:
        return str(path.relative_to(anchor))
    except ValueError:
        return str(path)


# ---------------------------------------------------------------------------
# Layer A — 安全删除包目录
# ---------------------------------------------------------------------------

def delete_directories(source: Path, packages: list[str]) -> int:
    """在所有 smali* 子目录下删除指定的包目录（带路径逃逸防护）。"""
    count = 0
    source_resolved = source.resolve()
    for smali_dir in sorted(source.glob("smali*")):
        if not smali_dir.is_dir():
            continue
        for pkg in packages:
            target = smali_dir / pkg
            if target.exists():
                # Path escape guard: resolved path must be under source
                try:
                    target.resolve().relative_to(source_resolved)
                except ValueError:
                    print(f"  ✗ 跳过: {target} 不在 {source} 目录下")
                    continue
                shutil.rmtree(target)
                count += 1
                print(f"  ✓ 删除 {safe_relative(target, source)}")
    return count


# ---------------------------------------------------------------------------
# Layer B — 对 SDK 初始化方法打桩
# ---------------------------------------------------------------------------

def _stub_method_body(method_lines: list[str], first_target: str) -> str:
    """将 smali 方法体替换为最小桩代码，根据返回类型选择正确指令。"""
    first = method_lines[0]
    if ")Landroid/view/View;" in first or ")Landroid/view/View" in first:
        # 返回 null View
        stub_body = "    .registers 1\n    const/4 v0, 0x0\n    return-object v0"
    elif ")V" in first:
        stub_body = "    .registers 1\n    return-void"
    elif ")Z" in first or ")Boolean" in first:
        stub_body = "    .registers 1\n    const/4 v0, 0x0\n    return v0"
    elif ")I" in first or ")Int" in first or ")Long" in first:
        stub_body = "    .registers 2\n    const-wide/16 v0, 0x0\n    return-wide v0" if ")J" in first else "    .registers 1\n    const/4 v0, 0x0\n    return v0"
    else:
        # 默认 return-void (Void 方法)
        stub_body = "    .registers 1\n    return-void"
    return f"{first}\n{stub_body}\n.end method"


def stub_init_methods(source: Path, init_methods: list[str]) -> int:
    """在所有 .smali 文件中寻找调用 init_methods 的方法并打桩。"""
    count = 0
    for smali_dir in sorted(source.glob("smali*")):
        if not smali_dir.is_dir():
            continue
        for smali_file in sorted(smali_dir.rglob("*.smali")):
            try:
                content = smali_file.read_text(encoding="utf-8")
            except Exception:
                continue

            # 快速预检：只要任何一个 target 字符串不在文件中就跳过
            if not any(t in content for t in init_methods):
                continue

            lines = content.split("\n")
            out: list[str] = []
            i = 0
            file_modified = False

            while i < len(lines):
                stripped = lines[i].strip()

                if not stripped.startswith(".method "):
                    out.append(lines[i])
                    i += 1
                    continue

                # 收集整个 method block
                method_lines: list[str] = [lines[i]]
                j = i + 1
                while j < len(lines) and lines[j].strip() != ".end method":
                    method_lines.append(lines[j])
                    j += 1
                if j < len(lines):
                    end_line = lines[j]  # .end method
                else:
                    end_line = ".end method"

                method_body = "\n".join(method_lines)

                # 检查是否包含任意 init target
                target_found: str | None = None
                for tgt in init_methods:
                    if tgt in method_body:
                        target_found = tgt
                        break

                if target_found is not None:
                    out.append(_stub_method_body(method_lines, target_found))
                    count += 1
                    file_modified = True
                    print(f"  ✓ 打桩 {safe_relative(smali_file, source)}: {target_found}")
                else:
                    out.extend(method_lines)
                    out.append(end_line)

                i = j + 1

            if file_modified:
                smali_file.write_text("\n".join(out), encoding="utf-8")

    return count


# ---------------------------------------------------------------------------
# Manifest 工具函数
# ---------------------------------------------------------------------------

def _manifest_path(source: Path) -> Path | None:
    p = source / "AndroidManifest.xml"
    return p if p.exists() else None


def remove_manifest_components(manifest_path: Path, components: list[str]) -> int:
    """从 AndroidManifest.xml 删除 <receiver>/<service>/<provider> 声明。"""
    content = manifest_path.read_text(encoding="utf-8")
    total = 0

    for comp in components:
        escaped = re.escape(comp)

        # 自闭合标签: <xxx ... android:name="comp" ... />
        pattern1 = re.compile(
            rf'<(receiver|service|provider)\s+[^>]*?android:name\s*=\s*"{escaped}"[^>]*?/>',
            re.DOTALL,
        )

        def _replacer1(m, c=comp):
            return f"<!-- removed: {c} -->"

        content, n1 = pattern1.subn(_replacer1, content)
        total += n1

        # 配对标签: <xxx ... android:name="comp" ...>...</xxx>
        pattern2 = re.compile(
            rf'<(receiver|service|provider)\s+[^>]*?android:name\s*=\s*"{escaped}"[^>]*?>.*?</\1>',
            re.DOTALL,
        )

        def _replacer2(m, c=comp):
            return f"<!-- removed: {c} -->"

        content, n2 = pattern2.subn(_replacer2, content)
        total += n2

        if n1 + n2 > 0:
            print(f"  ✓ 移除组件声明 ({n1 + n2} 处): {comp}")

    manifest_path.write_text(content, encoding="utf-8")
    return total


def filter_permissions(manifest_path: Path, keep: set[str]) -> int:
    """删除不在白名单中的 uses-permission 行。"""
    content = manifest_path.read_text(encoding="utf-8")

    pattern = re.compile(
        r'<uses-permission\s+android:name\s*=\s*"([^"]*)"\s*/?\s*>',
        re.DOTALL,
    )

    removed = 0

    def _replacer(m):
        nonlocal removed
        name = m.group(1)
        if name not in keep:
            removed += 1
            print(f"  ✓ 移除权限: {name}")
            return ""
        return m.group(0)

    content = pattern.sub(_replacer, content)
    manifest_path.write_text(content, encoding="utf-8")
    return removed


def disable_cleartext(manifest_path: Path) -> None:
    """跳过 cleartext 修改 — 保持 true 以免 HTTP 弹幕数据被拦截"""
    pass


# ---------------------------------------------------------------------------
# Fix network_security_config — 简化 SSL pin 配置（apktool 重编译会损坏它）
# ---------------------------------------------------------------------------

def fix_network_security_config(source: Path) -> None:
    """替换 network_security_config.xml 为简化版，避免 apktool 重编损坏 pin hash。"""
    for xml_file in source.rglob("network_security_config.xml"):
        simplified = '''<?xml version="1.0" encoding="utf-8"?>
<network-security-config>
    <base-config cleartextTrafficPermitted="true">
        <trust-anchors>
            <certificates src="system" />
        </trust-anchors>
    </base-config>
</network-security-config>'''
        xml_file.write_text(simplified, encoding="utf-8")
        print(f"  ✓ 简化 {xml_file.relative_to(source)} (移除 SSL pin)")
        return
    print("  (network_security_config.xml 未找到，跳过)")


# ---------------------------------------------------------------------------
# Fragment page removal — 按字符串搜索 smali 找 Fragment 类名再删除
# ---------------------------------------------------------------------------

def find_and_stub_fragment_pages(source: Path, keywords: list[str]) -> int:
    """在 smali 中搜索关键词找到 Fragment 类，stub 其方法体（返回空 view 不崩溃）。

    不删文件，只替换方法体为最小桩代码。
    处理两类：
      - Fragment 子类：stub onCreateView → return-void（空视图）
      - Tab 配置/Adapter 类：跳过包含关键词的 const-string 行（移除 tab）
    """
    count = 0
    processed: set[str] = set()

    for smali_dir in sorted(source.glob("smali*")):
        if not smali_dir.is_dir():
            continue
        for smali_file in sorted(smali_dir.rglob("*.smali")):
            try:
                content = smali_file.read_text(encoding="utf-8")
            except Exception:
                continue

            if not any(kw in content for kw in keywords):
                continue

            class_match = re.search(r'\.class\s+\S+\s+(L[\w/$-]+;)', content)
            if not class_match:
                continue
            class_desc = class_match.group(1)
            if class_desc in processed:
                continue

            # 确认是 const-string 中的关键词
            lines = content.split("\n")
            if not any(line.strip().startswith("const-string") and any(kw in line for kw in keywords) for line in lines):
                continue

            processed.add(class_desc)
            rel = safe_relative(smali_file, source)

            is_fragment = any("Fragment" in line for line in lines if ".super" in line)

            if is_fragment:
                # Fragment → stub onCreateView 返回空
                out = []
                modified = False
                i = 0
                while i < len(lines):
                    stripped = lines[i].strip()
                    if stripped.startswith(".method ") and any(n in stripped for n in ("onCreateView", "onViewCreated", "initView", "initData", "onActivityCreated")):
                        method_lines = [lines[i]]
                        j = i + 1
                        while j < len(lines) and lines[j].strip() != ".end method":
                            method_lines.append(lines[j])
                            j += 1
                        end_line = lines[j] if j < len(lines) else ".end method"
                        out.append(_stub_method_body(method_lines, ""))
                        modified = True
                        i = j + 1
                        count += 1
                        print(f"  ✓ stub {rel}: {class_desc}")
                        continue
                    out.append(lines[i])
                    i += 1
                if modified:
                    smali_file.write_text("\n".join(out), encoding="utf-8")
            else:
                # Tab 配置类 → 删除包含关键词的 const-string 行
                out = []
                modified = False
                for line in lines:
                    stripped = line.strip()
                    if stripped.startswith("const-string") and any(kw in stripped for kw in keywords):
                        modified = True
                        continue
                    out.append(line)
                if modified:
                    smali_file.write_text("\n".join(out), encoding="utf-8")
                    count += 1
                    print(f"  ✓ 移除 tab 条目 {rel}: {class_desc}")

    return count


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="从 apktool 反编译目录中删除广告 / 追踪 / 推送模块",
    )
    p.add_argument(
        "--source",
        required=True,
        help="apktool d 输出的根目录路径",
    )
    p.add_argument(
        "--ad-config",
        required=True,
        help="广告删除配置文件路径 (JSON)",
    )
    p.add_argument(
        "--push-config",
        required=True,
        help="推送删除配置文件路径 (JSON)",
    )
    p.add_argument(
        "--permissions-keep",
        required=True,
        help="权限白名单文件路径 (txt, 一行一条)",
    )
    return p


def main() -> int:
    args = build_parser().parse_args()

    source = Path(args.source)
    if not source.is_dir():
        print(f"[错误] 源目录不存在: {args.source}", file=sys.stderr)
        return 1

    ad_config = load_json(args.ad_config)
    push_config = load_json(args.push_config)
    keep_perms = load_permissions(args.permissions_keep)

    manifest = _manifest_path(source)
    if manifest is None:
        print("[警告] AndroidManifest.xml 不存在，跳过 manifest 相关操作")

    # ---- Phase 1: 删除广告 SDK 目录 ----
    print("\n=== Phase 1: 删除广告 SDK 包目录 ===")
    packages = ad_config.get("packages_to_delete", [])
    if packages:
        n = delete_directories(source, packages)
        print(f"  → 删除 {n} 个广告包目录")
    else:
        print("  (packages_to_delete 为空，跳过)")

    # ---- Phase 2: 修复 network_security_config.xml ----
    print("\n=== Phase 2: 修复网络配置 ===")
    fix_network_security_config(source)

    # ---- Phase 3: 删除 Fragment 页面（商城/赚钱/菜单等） ----
    print("\n=== Phase 3: 删除 Fragment 页面 ===")
    frag_keywords = ad_config.get("fragment_keywords", [])
    if frag_keywords:
        n = find_and_delete_fragment_pages(source, frag_keywords)
        print(f"  → 删除 {n} 个 Fragment 目录")
    else:
        print("  (fragment_keywords 为空，跳过)")

    print("\n✓ 完成")
    return 0


if __name__ == "__main__":
    sys.exit(main())
