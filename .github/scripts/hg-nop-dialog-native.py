#!/usr/bin/env python3
"""Block 鹿属 remote dialogs via network_security_config domain block only.
NO native code patching — always causes SIGSEGV (libseccore.so uses dlsym).
"""
import sys
from pathlib import Path

APK = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/apktool_out")
TOTAL = 0

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

print(f"\nComplete: {TOTAL} patches")
