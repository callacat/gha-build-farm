import os, shutil

modded = 'modded_smali'
official = 'official_smali'

# Only copy smali directories — NOT res/ lib/ assets/ etc.
for item in sorted(os.listdir(modded)):
    if not item.startswith('smali'):
        continue
    src = os.path.join(modded, item)
    dst = os.path.join(official, item)
    if not os.path.isdir(src):
        continue
    print('Merging ' + item)
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(src, dst)

# AndroidManifest — only update appComponentFactory
manifest_path = os.path.join(official, 'AndroidManifest.xml')
with open(manifest_path) as f:
    content = f.read()

old = 'android:appComponentFactory="androidx.core.app.CoreComponentFactory"'
new = 'android:appComponentFactory="com.pandora.core.AppFactory"'
if old in content:
    content = content.replace(old, new)
    with open(manifest_path, 'w') as f:
        f.write(content)
    print('Updated appComponentFactory in AndroidManifest.xml')
else:
    print('appComponentFactory already set or not found (checking modded value)')
    # Fall back to modded's manifest
    import shutil
    shutil.copy2(os.path.join(modded, 'AndroidManifest.xml'), manifest_path)
    print('Applied modded AndroidManifest.xml')

print('DONE')
