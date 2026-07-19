#!/usr/bin/env python3
"""Block 鹿属 remote dialogs. Patch gethostbyname PLT -> return NULL.
Native code uses gethostbyname() for DNS resolution via standard PLT.
Returning NULL (host not found) is standard POSIX error handling.
Socket stays functional — only DNS resolution fails."""
import struct, sys
from pathlib import Path

APK = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/apktool_out")
TOTAL = 0

# ── Phase 1: network_security_config domain block (Java layer) ──
print("=== Phase 1: network_security_config domain block ===")
for xml_file in APK.rglob("res/xml/e.xml"):
    text = xml_file.read_text("utf-8", errors="replace")
    if "oneseeker.top" in text:
        print(f"  Already blocked")
    else:
        block = """    <domain-config cleartextTrafficPermitted="false">
        <domain includeSubdomains="true">oneseeker.top</domain>
        <domain includeSubdomains="true">changzhi.top</domain>
        <domain includeSubdomains="true">xseclink.cn</domain>
        <domain includeSubdomains="true">xseclink.com</domain>
        <domain includeSubdomains="true">wtturl.cn</domain>
        <domain includeSubdomains="true">id6.me</domain>
        <domain includeSubdomains="true">praisewindow.ugsdk.cn</domain>
        <domain includeSubdomains="true">zlink.ugsdk.cn</domain>
        <domain includeSubdomains="true">chengzijianzhan.com</domain>
        <trust-anchors>
        </trust-anchors>
    </domain-config>
"""
        text = text.replace("</network-security-config>", block + "</network-security-config>")
        xml_file.write_text(text, encoding="utf-8")
        print(f"  ✅ Blocked domains added")
        TOTAL += 1
    break

# ── Phase 2: Patch libseccore.so gethostbyname -> NULL ──
print("\n=== Phase 2: Patch libseccore.so gethostbyname -> NULL ===")
# AArch64: mov x0, xzr (e0 03 1f aa) + ret (c0 03 5f d6) + nop * 2 (1f 20 03 d5)
NULL_STUB = bytes([0xe0,0x03,0x1f,0xaa, 0xc0,0x03,0x5f,0xd6, 0x1f,0x20,0x03,0xd5, 0x1f,0x20,0x03,0xd5])

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

    # Find gethostbyname symbol index
    host_idx = None
    for i in range(0, len(ds), 24):
        st_name = struct.unpack_from('<I', ds[i:i+4])[0]
        st_shndx = struct.unpack_from('<H', ds[i+6:i+8])[0]
        if st_shndx == 0 and st_name > 0:
            n = dstr[st_name:dstr.find(b'\x00', st_name)].decode('ascii', errors='replace')
            if n == 'gethostbyname': host_idx = i // 24; break

    if host_idx is None:
        print(f"  gethostbyname not in {so_file.relative_to(APK)}")
        continue

    # Find PLT entry for this symbol
    for i in range(0, len(rd), 24):
        r_info = struct.unpack_from('<Q', rd[i+8:i+16])[0]
        if (r_info >> 32) == host_idx:
            plt_off = po['offset'] + 32 + (i // 24) * 16
            if plt_off + 16 <= len(data):
                data[plt_off:plt_off+16] = NULL_STUB
                TOTAL += 1
                print(f"  ✅ {so_file.relative_to(APK)} gethostbyname -> NULL (PLT[{i//24}])")
            break

    so_file.write_bytes(bytes(data))

print(f"\nComplete: {TOTAL} patches")
