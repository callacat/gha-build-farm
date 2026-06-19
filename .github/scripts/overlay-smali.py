import os, shutil

modded = 'modded_smali'
official = 'official_smali'

for item in sorted(os.listdir(modded)):
    src = os.path.join(modded, item)
    dst = os.path.join(official, item)
    if item == 'original' or not os.path.isdir(src):
        continue
    print('Merging ' + item)
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(src, dst)

# AndroidManifest
shutil.copy2(os.path.join(modded, 'AndroidManifest.xml'),
             os.path.join(official, 'AndroidManifest.xml'))
print('Applied modded AndroidManifest.xml')
print('DONE')
