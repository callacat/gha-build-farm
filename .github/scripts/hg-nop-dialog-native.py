#!/usr/bin/env python3
"""Remove 鹿属 backdoor packages + block remote dialogs + kill native socket.

1. Delete CJPaySDK (com.android.ttcjpaysdk) — 鹿属第三方支付SDK，含所有后门URL
2. network_security_config — domain block at Java HTTP layer
3. socket() PLT patch — block native layer socket creation
"""
import struct, sys, re, shutil
from pathlib import Path

APK = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/apktool_out")
TOTAL = 0

# ── Phase 0: Delete CJPaySDK (后门 + 第三方 URL 来源) ──
print("=== Phase 0: Remove 鹿属 CJPaySDK ===")
TARGETS = ["com/android/ttcjpaysdk"]
removed = 0
for smali_dir in sorted(APK.glob("smali*")):
    if not smali_dir.is_dir():
        continue
    for pkg in TARGETS:
        target = smali_dir / pkg
        if target.is_dir():
            count = sum(1 for _ in target.rglob("*.smali"))
            shutil.rmtree(target)
            removed += 1
            TOTAL += count
            print(f"  ✅ Deleted {smali_dir.name}/{pkg} ({count} files)")

# Clean Manifest CJPay references
manifest = APK / "AndroidManifest.xml"
if manifest.exists():
    text = manifest.read_text("utf-8", errors="replace")
    # Remove CJPay-specific permissions
    text = re.sub(r'<uses-permission android:name="[^"]*cjpay[^"]*"/>\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'<permission android:label="[^"]*"[^>]*/>\s*', '', text)
    # Comment out CJPay component declarations
    text = re.sub(r'(<(?:activity|service|receiver|provider)\s+[^>]*?ttcjpaysdk[^>]*/?>)',
                  r'<!-- removed: \1 -->', text)
    manifest.write_text(text, encoding="utf-8")
    print(f"  ✅ CJPay components removed from Manifest")
    TOTAL += 1

print(f"  → Total CJPay SDK files removed: ~{TOTAL}")
TOTAL = 0  # Reset counter for next phases

# ── Phase 1: network_security_config domain block ──
print("\n=== Phase 1: network_security_config domain block ===")
for xml_file in APK.rglob("res/xml/e.xml"):
    text = xml_file.read_text("utf-8", errors="replace")
    if "oneseeker.top" in text:
        print(f"  Already blocked")
    else:
        block = """    <domain-config cleartextTrafficPermitted="false">
        <domain includeSubdomains="true">oneseeker.top</domain>
        <domain includeSubdomains="true">changzhi.top</domain>
        <trust-anchors>
        </trust-anchors>
    </domain-config>
"""
        text = text.replace("</network-security-config>", block + "</network-security-config>")
        xml_file.write_text(text, encoding="utf-8")
        print(f"  ✅ Blocked: oneseeker.top, changzhi.top")
        TOTAL += 1
    break

# ── Phase 2: Patch libseccore.so socket() -> -1 ──
print("\n=== Phase 2: Patch libseccore.so socket() -> return -1 ===")
NULL_STUB = bytes([0x00,0x00,0x80,0x12, 0xc0,0x03,0x5f,0xd6, 0x1f,0x20,0x03,0xd5, 0x1f,0x20,0x03,0xd5])

for so_file in sorted(APK.rglob("libseccore.so")):
    data = bytearray(so_file.read_bytes())
    e_shoff = struct.unpack_from('<Q', data, 0x28)[0]
    e_shentsize = struct.unpack_from('<H', data, 0x3A)[0]
    e_shnum = struct.unpack_from('<H', data, 0x3C)[0]
    e_shstrndx = struct.unpack_from('<H', data, 0x3E)[0]
    sec = []
    for i in range(e_shnum):
        off = e_shoff + i * e_shentsize
        sh_name = struct.unpack_from('<I', data[off:off+4])[0]
        sh_type = struct.unpack_from('<I', data[off+4:off+8])[0]
        sh_flags = struct.unpack_from('<Q', data[off+8:off+16])[0]
        sh_addr = struct.unpack_from('<Q', data[off+16:off+24])[0]
        sh_offset = struct.unpack_from('<Q', data[off+24:off+32])[0]
        sh_size = struct.unpack_from('<Q', data[off+32:off+40])[0]
        sec.append(dict(name=sh_name, type=sh_type, flags=sh_flags, addr=sh_addr, offset=sh_offset, size=sh_size))
    sst = data[sec[e_shstrndx]['offset']:sec[e_shstrndx]['offset']+sec[e_shstrndx]['size']]
    for s in sec:
        end = sst.find(b'\x00', s['name'])
        s['label'] = sst[s['name']:end].decode('ascii', errors='replace') if end > 0 else ''
    dso = next(s for s in sec if s.get('label') == '.dynsym')
    dto = next(s for s in sec if s.get('label') == '.dynstr')
    rpo = next(s for s in sec if s.get('label') == '.rela.plt')
    po = next(s for s in sec if s.get('label') == '.plt')
    ds = data[dso['offset']:dso['offset']+dso['size']]
    dstr = data[dto['offset']:dto['offset']+dto['size']]
    rd = data[rpo['offset']:rpo['offset']+rpo['size']]
    sym_map = {}
    for j in range(0, len(ds), 24):
        st_name = struct.unpack_from('<I', ds[j:j+4])[0]
        st_shndx = struct.unpack_from('<H', ds[j+6:j+8])[0]
        if st_shndx == 0 and st_name > 0:
            n = dstr[st_name:dstr.find(b'\x00', st_name)].decode('ascii', errors='replace')
            sym_map[n] = j // 24
    for fname in ['socket']:
        if fname not in sym_map: continue
        sidx = sym_map[fname]
        for j in range(0, len(rd), 24):
            r_info = struct.unpack_from('<Q', rd[j+8:j+16])[0]
            if (r_info >> 32) == sidx:
                plt_off = po['offset'] + 32 + (j // 24) * 16
                if plt_off + 16 <= len(data):
                    data[plt_off:plt_off+16] = NULL_STUB
                    TOTAL += 1
                    print(f"  ✅ {so_file.relative_to(APK)} {fname} -> -1")
                break
    so_file.write_bytes(bytes(data))

print(f"\nComplete: {TOTAL} patches")
