#!/usr/bin/env python3
"""
Patch BottomTabBarItemType.findByValue() smali to return null for ShopMall(5) and LuckyBenefit(2).
Run after apktool decode, before rebuild.
"""
import sys, os

def patch_findbyvalue(apktool_dir):
    """Modify findByValue smali to skip ShopMall and LuckyBenefit."""
    found = 0
    for root, dirs, files in os.walk(apktool_dir):
        for f in files:
            if f.endswith('.smali') and 'BottomTabBarItemType' in f:
                fpath = os.path.join(root, f)
                with open(fpath) as fh:
                    content = fh.read()

                if '.method public static findByValue' not in content:
                    continue

                print(f"  Found: {fpath}")

                # Insert early return for LuckyBenefit(2) and ShopMall(5)
                # Before the switch statement, add:
                #   if-eq p0, 5, :return_null
                #   if-eq p0, 2, :return_null
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

                # Insert after the method declaration line
                old = content
                content = content.replace(
                    '.method public static findByValue(I)Lcom/dragon/read/rpc/model/BottomTabBarItemType;',
                    '.method public static findByValue(I)Lcom/dragon/read/rpc/model/BottomTabBarItemType;\n' + insert_text
                )

                if content != old:
                    with open(fpath, 'w') as fh:
                        fh.write(content)
                    print(f"    ✓ Patched findByValue to skip ShopMall(5)/LuckyBenefit(2)")
                    found += 1
                else:
                    print(f"    ✗ Method signature not found")
                break

    if found == 0:
        print("  ⚠ BottomTabBarItemType smali not found, trying alternative search...")
        # Broader search
        for root, dirs, files in os.walk(apktool_dir):
            for f in files:
                if f.endswith('.smali'):
                    fpath = os.path.join(root, f)
                    with open(fpath) as fh:
                        content = fh.read()
                    if 'findByValue' in content and 'BottomTabBarItemType' in content:
                        print(f"  Found references in: {fpath}")

    return found > 0

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: patch-smali-findbyvalue.py <apktool-dir-or-smali-file>")
        sys.exit(1)
    arg = sys.argv[1]
    if arg.endswith('.smali') and os.path.isfile(arg):
        # Single file mode (called from build.sh)
        with open(arg) as fh:
            content = fh.read()
        if '.method public static findByValue' in content:
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
                '.method public static findByValue(I)Lcom/dragon/read/rpc/model/BottomTabBarItemType;',
                '.method public static findByValue(I)Lcom/dragon/read/rpc/model/BottomTabBarItemType;\n' + insert_text
            )
            if new_content != content:
                with open(arg, 'w') as fh:
                    fh.write(new_content)
                print(f"    ✓ Patched {os.path.basename(arg)}")
                sys.exit(0)
            else:
                print(f"    ✗ Signature not found in {os.path.basename(arg)}")
                sys.exit(1)
        else:
            sys.exit(1)
    else:
        # Directory mode
        result = patch_findbyvalue(arg)
        sys.exit(0 if result else 1)
