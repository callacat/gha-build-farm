import os, hashlib

modded = 'modded_smali'
official = 'official_smali'

# Only consider files containing these keywords
KEY_PATTERNS = [
    'checkSign', 'CheckSign', 'check_sign',
    'NovelCommonParam', 'checkSignEnv', 'checkSignRes',
    'getPackageInfo', 'PackageManager',
    'CreatorProxy', 'AppFactory',
    'Lancet', '@Proxy',
    'signatures', 'signingInfo',
    'appComponentFactory',
    'DeviceRegisterManager',
]

def grep(path, pat):
    """Quick check if file contains pattern (only first 8KB)."""
    try:
        with open(path) as f:
            buf = f.read(8192)
            while buf:
                if pat in buf:
                    return True
                buf = f.read(8192)
    except:
        pass
    return False

def is_interesting(path):
    if not path.endswith('.smali'):
        return False
    for pat in KEY_PATTERNS:
        if grep(path, pat):
            return True
    return False

# Phase 1: scan modded for interesting files (fast, 8KB each)
interesting = set()
scanned = 0
for root, dirs, files in os.walk(modded):
    for f in files:
        scanned += 1
        path = os.path.join(root, f)
        if is_interesting(path):
            rel = os.path.relpath(path, modded)
            interesting.add(rel)

print('Scanned {} files, found {} interesting'.format(scanned, len(interesting)))

# Phase 2: byte-for-byte compare interesting files
true_mods = []
for rel in sorted(interesting):
    mod_path = os.path.join(modded, rel)
    off_path = os.path.join(official, rel)
    if not os.path.exists(off_path):
        print('PATCH-ONLY: {}'.format(rel))
        continue
    with open(mod_path, 'rb') as a, open(off_path, 'rb') as b:
        if a.read() != b.read():
            print('MODIFIED: {}'.format(rel))
            true_mods.append(rel)

print('\nTOTAL_MODIFIED: {}'.format(len(true_mods)))
