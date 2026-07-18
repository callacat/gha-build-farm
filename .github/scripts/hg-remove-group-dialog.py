#!/usr/bin/env python3
"""去除鹿属（sgcore0）软件使用声明 / 邀请加入群聊弹窗"""
import shutil
from pathlib import Path
import sys

APKTOOL = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/apktool_out")

# 鹿属弹窗的 smali 包路径（在 apktool decode 后的目录下）
# 注意：只删弹窗 UI 代码，保留 sgcore0/SafeLoader 和 libseccore.so
#       libseccore.so 是鹿属去广告的 native 层，删了广告会回来
MODDER_SMALI_PACKAGES = [
    "org/checkerframework/checker/signature/query/security",  # 弹窗主体 + 按钮逻辑
]

removed_files = 0
removed_dirs = 0

# 1. 删除 smali 文件
print("=== 1. 删除鹿属 smali 代码 ===")
for smali_dir in sorted(APKTOOL.glob("smali*")):
    if not smali_dir.is_dir():
        continue
    for pkg in MODDER_SMALI_PACKAGES:
        target = smali_dir / pkg
        if target.is_dir():
            file_count = sum(1 for _ in target.rglob("*.smali"))
            print(f"  删除 {target} ({file_count} 个 smali 文件)")
            shutil.rmtree(target)
            removed_files += file_count
            removed_dirs += 1

# 2. 不删除 libseccore.so — 它是鹿属去广告的 native 层
#    ponytail: 不删就不崩
print("\n=== 2. 保留 libseccore.so（去广告 native 层，不删） ===")
for so_file in APKTOOL.rglob("libseccore.so"):
    print(f"  保留 {so_file}")

# 3. 从 AndroidManifest.xml 中移除可能存在的 Activity 声明
manifest = APKTOOL / "AndroidManifest.xml"
if manifest.is_file():
    content = manifest.read_text("utf-8", errors="replace")
    # 鹿属弹窗可能注册了 Activity（查找签名/安全相关 Activity）
    suspicious_patterns = [
        "checkerframework.checker.signature.query.security",
    ]
    original_len = len(content)
    for pattern in suspicious_patterns:
        if pattern.lower() in content.lower():
            print(f"  ⚠️  AndroidManifest.xml 中发现 {pattern} 引用")
            # 打印上下文
            for i, line in enumerate(content.split("\n"), 1):
                if pattern.lower() in line.lower():
                    print(f"      行 {i}: {line.strip()[:150]}")

# 4. 清理 META-INF 中可能存在的签名（重建会重新签名）
meta_inf = APKTOOL / "META-INF"
if meta_inf.is_dir():
    for sf_file in meta_inf.glob("*.SF"):
        sf_file.unlink()
        removed_files += 1
    for rsa_file in meta_inf.glob("*.RSA"):
        rsa_file.unlink()
        removed_files += 1

print(f"\n=== 完成 ===")
print(f"  删除文件数: {removed_files}")
print(f"  删除目录数: {removed_dirs}")
if removed_files == 0:
    print("  ⚠️  没有找到任何鹿属代码，可能是已去过的版本，或 smali 包名有变化")
