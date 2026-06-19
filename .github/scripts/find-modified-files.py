import os

modded = 'modded_smali'
official = 'official_smali'

count = 0
for root, dirs, files in os.walk(modded):
    for f in files:
        if not f.endswith('.smali'):
            continue
        mod_path = os.path.join(root, f)
        off_path = mod_path.replace('modded_smali', 'official_smali', 1)
        if not os.path.exists(off_path):
            continue
        with open(mod_path) as a, open(off_path) as b:
            if a.read() != b.read():
                rel = os.path.relpath(mod_path, modded)
                print(rel)
                count += 1

print('TOTAL_MODIFIED: {}'.format(count))
