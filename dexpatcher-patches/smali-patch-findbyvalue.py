#!/usr/bin/env python3
"""
Smali post-patch: modify BottomTabBarItemType.findByValue() to return null
for ShopMall(5) and LuckyBenefit(2).

Usage: smali-patch-findbyvalue.py <dex-files-dir> <sdk-dir>
"""
import sys, os, subprocess, tempfile, shutil

def find_bak_smali(sdk):
    """Find baksmali and smali jars."""
    bt = os.path.join(sdk, "build-tools")
    if not os.path.isdir(bt):
        return None, None
    versions = sorted(os.listdir(bt), reverse=True)
    for v in versions:
        d = os.path.join(bt, v)
        bak = os.path.join(d, "baksmali.jar")
        sm = os.path.join(d, "smali.jar")
        if os.path.exists(bak) and os.path.exists(sm):
            return bak, sm
    return None, None


def patch_dex(dex_path, baksmali_jar, smali_jar):
    """Patch BottomTabBarItemType in one dex file."""
    tmpdir = tempfile.mkdtemp()
    try:
        # Disassemble
        r = subprocess.run(
            ["java", "-jar", baksmali_jar, "d", dex_path, "-o", tmpdir],
            capture_output=True, text=True, timeout=120
        )
        if r.returncode != 0:
            return False

        # Find BottomTabBarItemType.smali
        for root, dirs, files in os.walk(tmpdir):
            for f in files:
                if f.endswith(".smali") and "BottomTabBarItemType" in f:
                    fpath = os.path.join(root, f)
                    with open(fpath) as fh:
                        content = fh.read()

                    if ".method public static findByValue" not in content:
                        continue

                    insert = [
                        "    # filtered by hg-ad-removal",
                        "    const/4 v0, 0x5",
                        "    if-ne p0, v0, :check_lucky",
                        "    const/4 v0, 0x0",
                        "    return-object v0",
                        "    :check_lucky",
                        "    const/4 v0, 0x2",
                        "    if-ne p0, v0, :original_switch",
                        "    const/4 v0, 0x0",
                        "    return-object v0",
                        "    :original_switch",
                    ]
                    insert_text = "\n".join(insert) + "\n"

                    new_content = content.replace(
                        ".method public static findByValue(I)Lcom/dragon/read/rpc/model/BottomTabBarItemType;",
                        ".method public static findByValue(I)Lcom/dragon/read/rpc/model/BottomTabBarItemType;\n" + insert_text
                    )
                    if new_content != content:
                        with open(fpath, "w") as fh:
                            fh.write(new_content)
                        print(f"    ✓ findyValue patched in {os.path.basename(fpath)}")

                        # Reassemble
                        r2 = subprocess.run(
                            ["java", "-jar", smali_jar, "a", tmpdir, "-o", dex_path],
                            capture_output=True, text=True, timeout=120
                        )
                        if r2.returncode == 0:
                            print(f"    ✓ Dex rebuilt: {os.path.basename(dex_path)} ({os.path.getsize(dex_path)} bytes)")
                            return True
                        else:
                            print(f"    ✗ Reassembly failed: {r2.stderr[:200]}")
                            return False
        return False
    finally:
        for f in os.listdir(tmpdir):
            fp = os.path.join(tmpdir, f)
            try:
                if os.path.isfile(fp):
                    os.unlink(fp)
                elif os.path.isdir(fp):
                    import shutil
                    shutil.rmtree(fp)
            except:
                pass
        os.rmdir(tmpdir)


def main():
    dex_dir = sys.argv[1]
    sdk = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("ANDROID_HOME", "/usr/local/lib/android/sdk")

    baksmali_jar, smali_jar = find_bak_smali(sdk)

    if not baksmali_jar or not smali_jar:
        print("  baksmali/smali not found, skipping smali patch")
        return

    patched_any = False
    for f in sorted(os.listdir(dex_dir)):
        if not f.endswith(".dex") or f.endswith(".patched"):
            continue
        fp = os.path.join(dex_dir, f)
        # Quick check if this dex contains BottomTabBarItemType
        with open(fp, "rb") as fh:
            header = fh.read()
        if b"BottomTabBarItemType" not in header:
            continue
        print(f"  BottomTabBarItemType found in {f}")
        if patch_dex(fp, baksmali_jar, smali_jar):
            patched_any = True

    if not patched_any:
        print("  ⚠ No BottomTabBarItemType.findByValue found to patch")


if __name__ == "__main__":
    main()
