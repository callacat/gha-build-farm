#!/usr/bin/env python3
"""Search decompiled APK for signature verification / security checks."""
import os, re, json
from collections import Counter

SEARCH_DIRS = ['/tmp/jadx_out', '/tmp/apktool_out']
RESULTS = {}

def search_strings(search_dir, label):
    """Search for Chinese security warning strings."""
    if not os.path.isdir(search_dir):
        return

    patterns = {
        '不安全': b'不安全'.decode(),
        '当前版本不安全': b'当前版本不安全'.decode(),
        '应用市场': b'应用市场'.decode(),
        'signature': None,  # search all files
    }

    # Phase 1: Find exact Chinese string matches
    chinese_targets = ['不安全', '当前版本', '应用市场', '正规市场', '安全检测',
                       '版本检测', '非法版本', '盗版', '签名验证', '签名校验',
                       'verification failed', 'signature.*invalid', 'checksum',
                       'self.check', 'safe mode', 'integrity', 'tamper']

    print(f'\n=== Searching in {label} ===')

    # Search by extension
    for ext in ['*.java', '*.smali', '*.xml', '*.json']:
        for root, dirs, files in os.walk(search_dir):
            for f in files:
                if not f.endswith(ext.replace('*', '')):
                    continue
                path = os.path.join(root, f)
                try:
                    with open(path, 'rb') as fh:
                        content = fh.read()
                    for target in chinese_targets:
                        if target.encode('utf-8') in content:
                            rel = os.path.relpath(path, search_dir)
                            line_no = 0
                            # Try to find line number
                            lines = content.split(b'\n')
                            for i, line in enumerate(lines):
                                if target.encode('utf-8') in line:
                                    line_no = i + 1
                                    snippet = line.strip().decode('utf-8', errors='replace')[:120]
                                    print(f'  [{ext}] {rel}:{line_no} → {snippet}')
                                    break
                except Exception:
                    pass

    # Phase 2: Search for PackageManager signature checks
    pm_patterns = [
        b'getPackageInfo', b'GET_SIGNATURES', b'getSignatures',
        b'PackageManager', b'signatures\[', b'signatures',
        b'SIGNING_CERTIFICATES', b'PackageInfo', b'flags\s*=',
    ]
    print(f'\n=== Signature check patterns in {label} ===')
    for root, dirs, files in os.walk(search_dir):
        for f in files:
            if not f.endswith(('.smali', '.java')):
                continue
            path = os.path.join(root, f)
            try:
                with open(path, 'rb') as fh:
                    content = fh.read()
                for pat in pm_patterns:
                    if pat in content and b'adsdk' not in content.lower() and b'ttad' not in content.lower():
                        rel = os.path.relpath(path, search_dir)
                        lines = content.split(b'\n')
                        for i, line in enumerate(lines):
                            if pat in line:
                                snippet = line.strip().decode('utf-8', errors='replace')[:120]
                                print(f'  {rel}:{i+1} → {snippet}')
                                break
                        break  # one match per file to reduce noise
            except Exception:
                pass

    # Phase 3: Search for "当前版本不安全" exact text in smali
    print(f'\n=== 当前版本不安全 in {label} ===')
    for root, dirs, files in os.walk(search_dir):
        for f in files:
            if not f.endswith('.smali'):
                continue
            path = os.path.join(root, f)
            try:
                with open(path, 'rb') as fh:
                    for i, line in enumerate(fh):
                        if b'\xe4\xb8\x8d\xe5\xae\x89\xe5\x85\xa8' in line:  # 不安全
                            rel = os.path.relpath(path, search_dir)
                            print(f'  {rel}:{i+1} → {line.strip().decode("utf-8", errors="replace")[:100]}')
            except Exception:
                pass


for d in SEARCH_DIRS:
    if os.path.isdir(d):
        search_strings(d, d.replace('/tmp/', ''))

print('\n=== Done ===')
