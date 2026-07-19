#!/usr/bin/env python3
"""红果短剧 官方版 vs 鹿属修改版 深度全量分析
Usage: python3 hg-deep-compare.py /tmp/official/ /tmp/modded/

分析维度：
  - 双 APK 的 jadx 反编译 + smali 全量对比
  - 混淆类映射关系（内容哈希配对）
  - 所有非 SDK 域名/IP 提取 + 分类
  - native .so 字符串提取 + 差异分析
  - 设备指纹/OAID/GAID 调用追踪
  - 签名校验绕过代码定位
  - 隐藏弹窗触发链追踪
  - 鹿属特定代码识别
"""
import re, json, sys, os, hashlib, struct
from pathlib import Path
from collections import defaultdict

OFFICIAL = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/official")
MODDED   = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("/tmp/modded")
FINDINGS = []

def L(tag, msg):
    FINDINGS.append(f"[{tag}] {msg}")

def slurp(p):
    try: return p.read_text("utf-8", errors="replace")
    except: return ""

def smali_hash(p):
    """Content-based hash of a smali file (ignore line numbers and comments)"""
    t = slurp(p)
    t = re.sub(r'\.line\s+\d+', '', t)
    t = re.sub(r'#.*', '', t)
    return hashlib.sha256(t.encode()).hexdigest()[:16]

def all_smali_files(base, prefix="smali"):
    for sd in sorted(base.glob(f"{prefix}*")):
        if sd.is_dir():
            yield from sd.rglob("*.smali")

def smali_package_map(base):
    """Map smali files by (package, classname, hash)"""
    pkg_map = defaultdict(list)
    for f in all_smali_files(base):
        t = slurp(f)
        # Extract class declaration
        cls = re.search(r'\.class\s+.*?L([\w/$]+);', t)
        if not cls: continue
        full_path = cls.group(1)
        parts = full_path.split('/')
        if len(parts) < 2: continue
        pkg = '.'.join(parts[:-1])
        clsname = parts[-1]
        fhash = smali_hash(f)
        pkg_map[pkg].append((clsname, fhash, str(f.relative_to(base))))
    return pkg_map

def find_smali(base, needle, exclude_androidx=True):
    """Search all smali files for a pattern"""
    results = []
    for f in all_smali_files(base):
        r = str(f.relative_to(base))
        if exclude_androidx and ("/androidx/" in r or "/android/support/" in r or "/kotlin/" in r):
            continue
        t = slurp(f)
        if needle in t:
            lines = [l.strip() for l in t.split('\n') if needle in l]
            results.append((r, lines[:3]))
    return results

def native_strings(base):
    """Extract all readable strings from native .so files"""
    strings = {}
    for lib_dir in base.glob("lib/*"):
        for so in lib_dir.rglob("*.so"):
            try:
                data = so.read_bytes()
                # Extract ASCII strings of length >= 6
                s = []
                cur = b''
                for b in data:
                    if 32 <= b < 127:
                        cur += bytes([b])
                    else:
                        if len(cur) >= 6:
                            s.append(cur.decode('ascii'))
                        cur = b''
                if cur and len(cur) >= 6:
                    s.append(cur.decode('ascii'))
                if s:
                    strings[str(so.relative_to(base))] = s
            except:
                pass
    return strings

# ============================================================
# PHASE 1: 基础结构对比
# ============================================================
print("=" * 70)
print("PHASE 1/6: 基础结构对比")
print("=" * 70)

# Manifest
for label, apk in [("官方版", OFFICIAL), ("修改版", MODDED)]:
    mf = apk / "AndroidManifest.xml"
    if mf.exists():
        t = slurp(mf)
        ver = re.search(r'version(?:Name|Code)="(\d[^"]*)"', t)
        pkg = re.search(r'package="([^"]+)"', t)
        app_comp = re.search(r'appComponentFactory="([^"]+)"', t)
        app_name = re.search(r'android:name="([^"]+)"', t)
        L("MANIFEST", f"{label}:")
        L("MANIFEST", f"  包名: {pkg.group(1) if pkg else '?'}")
        L("MANIFEST", f"  版本: {ver.group(1) if ver else '?'}")
        L("MANIFEST", f"  AppFactory: {app_comp.group(1) if app_comp else '?'}")
        L("MANIFEST", f"  Application: {app_name.group(1) if app_comp else '?'}")

# Smali file counts
for label, apk in [("官方版", OFFICIAL), ("修改版", MODDED)]:
    total = sum(1 for _ in all_smali_files(apk))
    L("COUNT", f"{label} smali: {total}")

# So file counts
for label, apk in [("官方版", OFFICIAL), ("修改版", MODDED)]:
    sos = list(apk.glob("lib/**/*.so"))
    sos_by_arch = defaultdict(list)
    for s in sos:
        parts = str(s.relative_to(apk)).split('/')
        if len(parts) >= 2:
            sos_by_arch[parts[1]].append(parts[-1])
    L("NATIVE", f"{label}: {len(sos)} .so files")
    for arch, files in sorted(sos_by_arch.items()):
        L("NATIVE", f"  {arch}: {len(files)} files")

# ============================================================
# PHASE 2: 包结构对比（混淆类映射）
# ============================================================
print("\n" + "=" * 70)
print("PHASE 2/6: 包结构对比 & 混淆映射")
print("=" * 70)

off_pkg = smali_package_map(OFFICIAL)
mod_pkg = smali_package_map(MODDED)

# Packages only in one
off_pkgs = set(off_pkg.keys())
mod_pkgs = set(mod_pkg.keys())

only_off = off_pkgs - mod_pkgs
only_mod = mod_pkgs - off_pkgs

L("PKG", f"官方版独有包: {len(only_off)}")
for p in sorted(only_off)[:30]:
    cls_count = len(off_pkg[p])
    L("PKG", f"  {p} ({cls_count} 类)")

L("PKG", f"修改版独有包: {len(only_mod)}")
for p in sorted(only_mod)[:50]:
    cls_count = len(mod_pkg[p])
    L("PKG", f"  {p} ({cls_count} 类)")

# Content-hash matching: find same-content classes between two versions
L("HASH", "=== 内容哈希交叉匹配（找已修改的类）===")
off_by_hash = defaultdict(list)
for pkg, classes in off_pkg.items():
    for clsname, fhash, path in classes:
        off_by_hash[fhash].append((pkg, clsname, path))

mod_by_hash = defaultdict(list)
for pkg, classes in mod_pkg.items():
    for clsname, fhash, path in classes:
        mod_by_hash[fhash].append((pkg, clsname, path))

same_hashes = set(off_by_hash.keys()) & set(mod_by_hash.keys())
only_off_h = set(off_by_hash.keys()) - set(mod_by_hash.keys())
only_mod_h = set(mod_by_hash.keys()) - set(off_by_hash.keys())

L("HASH", f"内容相同（hash匹配）: {len(same_hashes)} unique hashes")
L("HASH", f"仅官方版有: {len(only_off_h)} unique hashes")
L("HASH", f"仅修改版有: {len(only_mod_h)} unique hashes")

# ============================================================
# PHASE 3: 域名/IP 全面提取
# ============================================================
print("\n" + "=" * 70)
print("PHASE 3/6: 域名 & IP 全面提取")
print("=" * 70)

def extract_urls_from_text(text):
    urls = set(re.findall(r'https?://[a-zA-Z0-9][-a-zA-Z0-9.]*\.[a-zA-Z]{2,}[^\s"\'<>)]*', text))
    ips = set(re.findall(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', text))
    return urls, ips

SDK_DOMAINS = {
    "google", "android", "w3.org", "apache", "github", "bytedance", "byte",
    "snssdk", "pstatp", "zijieapi", "douyin", "toutiao", "amemv",
    "okhttp", "retrofit", "kotlin", "coroutine", "gradle", "maven",
    "spring", "kotlin", "lynx", "bytegecko", "bytecdn","pangle",
    "alipay", "weixin", "weibo", "taobao", "xiaohongshu","qpic",
    "qq.com", "tencent", "openmobile", "developer.android",
    "schemas.android", "exifinterface", "adobe", "goo.gle",
}

def classify_url(url):
    for d in SDK_DOMAINS:
        if d in url.lower():
            return "SDK"
    if any(kw in url for kw in [".cn/", ".top/", ".xyz/", ".cc/", ".me/", ".tk/"]):
        return "SUSPECT"
    return "OTHER"

def analyze_urls(apk, label):
    apk_urls = set()
    apk_ips = set()
    # Smali
    for f in all_smali_files(apk):
        t = slurp(f)
        u, i = extract_urls_from_text(t)
        apk_urls.update(u)
        apk_ips.update(i)
    # Native
    for lib_dir in apk.glob("lib/*"):
        for so in lib_dir.rglob("*.so"):
            try:
                strings = so.read_bytes()
                s_text = ''.join(chr(b) if 32 <= b < 127 else '\n' for b in strings)
                u, i = extract_urls_from_text(s_text)
                apk_urls.update(u)
                apk_ips.update(i)
            except: pass
    # Resources
    for res in apk.rglob("*.xml"):
        t = slurp(res)
        u, i = extract_urls_from_text(t)
        apk_urls.update(u)
        apk_ips.update(i)
    for arsc in apk.rglob("*.arsc"):
        t = slurp(arsc)
        u, i = extract_urls_from_text(t)
        apk_urls.update(u)
        apk_ips.update(i)

    L("URL", f"\n=== {label} ===")
    suspect = [u for u in apk_urls if classify_url(u) == "SUSPECT"]
    sdk = [u for u in apk_urls if classify_url(u) == "SDK"]
    other = [u for u in apk_urls if classify_url(u) == "OTHER"]

    L("URL", f"可疑域名/IP: {len(suspect)}")
    for u in sorted(suspect)[:30]:
        L("URL", f"  ⚠ {u}")

    L("URL", f"SDK 域名: {len(sdk)}")
    for u in sorted(sdk)[:20]:
        L("URL", f"  {u}")

    L("URL", f"非内网 IP: {len([i for i in apk_ips if not i.startswith(('10.', '192.168.', '172.1', '127.', '0.0'))])}")
    for ip in sorted(apk_ips):
        if ip.startswith(('10.', '192.168.', '127.')):
            L("URL", f"  内网: {ip}")
        else:
            L("URL", f"  公网: {ip}")

    return apk_urls, apk_ips

off_urls, off_ips = analyze_urls(OFFICIAL, "官方版")
mod_urls, mod_ips = analyze_urls(MODDED, "修改版")

# 域名对比
only_off_urls = off_urls - mod_urls
only_mod_urls = mod_urls - off_urls
L("URL_DIFF", f"\n=== URL 差异 ===")
L("URL_DIFF", f"仅官方有: {len(only_off_urls)}")
for u in sorted(only_off_urls)[:20]:
    L("URL_DIFF", f"  官方: {u}")
L("URL_DIFF", f"仅修改版有: {len(only_mod_urls)}")
for u in sorted(only_mod_urls)[:30]:
    L("URL_DIFF", f"  修改: {u}")

# ============================================================
# PHASE 4: Native 库字符串对比
# ============================================================
print("\n" + "=" * 70)
print("PHASE 4/6: Native 库字符串深度分析")
print("=" * 70)

for label, apk in [("官方版", OFFICIAL), ("修改版", MODDED)]:
    ns = native_strings(apk)
    L("NATIVE_STRINGS", f"\n=== {label} native strings ===")
    for soname, strs in sorted(ns.items()):
        # Filter interesting strings
        interesting = [s for s in strs if any(k in s.lower() for k in [
            "http", ".com", ".cn", ".top", "update", "dialog", "version",
            "check", "secret", "key", "token", "sign", "aes", "rsa",
            "encrypt", "decrypt", "hook", "inject", "root", "su ",
            "kill", "exec", "cmd", "sh ", "bash", "chmod"
        ])]
        if interesting:
            L("NATIVE_STRINGS", f"  {soname}:")
            for s in interesting[:10]:
                L("NATIVE_STRINGS", f"    [{s[:120]}]")

# ============================================================
# PHASE 5: 恶意行为检测
# ============================================================
print("\n" + "=" * 70)
print("PHASE 5/6: 恶意行为 & 安全检测")
print("=" * 70)

for label, apk in [("官方版", OFFICIAL), ("修改版", MODDED)]:
    L("SECURITY", f"\n=== {label} ===")

    # Device ID collection
    for pat, desc in [
        ("getDeviceId", "设备ID(IMEI)"),
        ("getImei", "IMEI"),
        ("getSubscriberId", "IMSI"),
        ("getSimSerialNumber", "SIM序列号"),
        ("AdvertisingId", "广告ID"),
        ("getAdvertisingIdInfo", "广告ID信息"),
        ("OAID", "OAID"),
        ("getOaid", "OAID获取"),
        ("getMacAddress", "MAC地址"),
        ("getWifiMac", "WiFi MAC"),
        ("getAccountsByType", "账户信息"),
        ("getLastKnownLocation", "位置"),
        ("requestLocationUpdates", "位置更新"),
        ("MANAGE_EXTERNAL_STORAGE", "文件管理权限"),
    ]:
        hits = find_smali(apk, pat)
        if hits:
            unique_files = len(set(h[0] for h in hits))
            L("SECURITY", f"  [{desc}] {unique_files} files")
            for f, lines in hits[:3]:
                L("SECURITY", f"    {f}")

    # Root detection
    for pat in ["su ", "Superuser", "root.*detect", "isRooted", "checkRoot",
                "build.TAGS.*test-keys", "magisk", "supolicy"]:
        hits = find_smali(apk, pat)
        if hits:
            L("ROOT", f"  Root检测/规避: {len(hits)} hits")
            for f, _ in hits[:5]:
                L("ROOT", f"    {f}")

    # HTTP cleartext
    hits = find_smali(apk, "http://")
    L("SECURITY", f"  HTTP(明文)请求: {len(hits)} hits")

    # Native method declarations
    count = 0
    for f in all_smali_files(apk):
        t = slurp(f)
        count += t.count("method.*native")
    L("NATIVE", f"  native方法声明: ~{count}")

    # LoadLibrary calls
    libs = set()
    for f in all_smali_files(apk):
        t = slurp(f)
        for m in re.finditer(r'System;->loadLibrary\("(\w+)"\)', t):
            libs.add(m.group(1))
    L("NATIVE", f"  loadLibrary: {sorted(libs)[:20]}")

# ============================================================
# PHASE 6: 鹿属特定代码定位
# ============================================================
print("\n" + "=" * 70)
print("PHASE 6/6: 鹿属修改特征定位")
print("=" * 70)

L("MODDER", "=== AppFactory 相关 ===")
for label, apk in [("官方版", OFFICIAL), ("修改版", MODDED)]:
    appf = list(apk.rglob("smali*/com/pandora/core/AppFactory*.smali"))
    if appf:
        L("MODDER", f"{label}: 找到 AppFactory ({len(appf)} files)")
        for f in appf[:5]:
            t = slurp(f)
            L("MODDER", f"  {f.relative_to(apk)}")
            for m in re.findall(r'\.method\s+.*\n(?:.*\n)*?(?=\.end method)', t, re.M):
                if 'hook' in m.lower() or 'getPackageInfo' in m or 'getApplicationInfo' in m or 'signature' in m.lower():
                    lines = m.split('\n')[:5]
                    for l in lines:
                        L("MODDER", f"    {l.strip()[:100]}")
    else:
        L("MODDER", f"{label}: 无 AppFactory")

# CJPaySDK check
L("MODDER", "\n=== CJPaySDK 相关 ===")
for label, apk in [("官方版", OFFICIAL), ("修改版", MODDED)]:
    cjpay = list(apk.rglob("smali*/com/android/ttcjpaysdk/**/*.smali"))
    if cjpay:
        L("MODDER", f"{label}: CJPaySDK 存在 ({len(cjpay)} files)")
    ug = list(apk.rglob("smali*/com/bytedance/caijing/**/*.smali"))
    if ug:
        L("MODDER", f"{label}: 字节财经SDK存在 ({len(ug)} files)")

# 鹿属后门域名
L("MODDER", "\n=== oneseeker/changzhi 后门 ===")
for label, apk in [("官方版", OFFICIAL), ("修改版", MODDED)]:
    for keyword in ["oneseeker", "changzhi", "HelloWorld", "CJPay", "cjpay", "ugsdk"]:
        hits = find_smali(apk, keyword, exclude_androidx=False)
        if hits:
            L("MODDER", f"{label} [{keyword}]: {len(hits)} hits")
            for f, lines in hits[:5]:
                L("MODDER", f"  {f}")
    # Also check .so files
    for so in apk.glob("lib/**/*.so"):
        try:
            data = so.read_bytes()
            for keyword in ["oneseeker", "changzhi", "HelloWorld", "10.18.32"]:
                if keyword.encode() in data:
                    L("MODDER", f"{label}: {keyword} IN {so.relative_to(apk)}")
        except: pass

# ============================================================
# WRITE REPORT
# ============================================================
print("\n" + "=" * 70)
print(f"分析完成: {len(FINDINGS)} 条发现")
print("=" * 70)

report = "\n".join(FINDINGS)
Path("/tmp/deep-compare-report.txt").write_text(report)

# Also write structured JSON for downstream
summary = {
    "official": {"smali_count": sum(1 for _ in all_smali_files(OFFICIAL)),
                 "so_count": len(list(OFFICIAL.glob("lib/**/*.so")))},
    "modded": {"smali_count": sum(1 for _ in all_smali_files(MODDED)),
               "so_count": len(list(MODDED.glob("lib/**/*.so")))},
    "findings_count": len(FINDINGS),
}
Path("/tmp/deep-compare-summary.json").write_text(json.dumps(summary, indent=2))
print(f"报告: /tmp/deep-compare-report.txt ({len(FINDINGS)} lines)")
print(f"摘要: /tmp/deep-compare-summary.json")
