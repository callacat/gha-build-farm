#!/usr/bin/env bash
set -euo pipefail

mkdir -p patches/references
cd modded_smali

for spec in \
  "checkSign:checkSign\|CheckSign\|check_sign" \
  "signEnv:checkSignEnv\|checkSignRes" \
  "novelParam:NovelCommonParam" \
  "packageInfo:getPackageInfo\|signatures\|signingInfo" \
  "signData:_sign\|signData\|sign_data" \
  "device:DeviceRegisterManager\|deviceId\|oaid" \
  "lancet:Lancet\|@Proxy" \
  "shadowhook:shadowhook\|ShadowHook"; do

  name="${spec%%:*}"
  pattern="${spec#*:}"
  grep -rn "$pattern" smali*/ --include="*.smali" 2>/dev/null | head -300 > "../patches/references/${name}.txt"
  count=$(wc -l < "../patches/references/${name}.txt")
  printf "  %-20s %d lines\n" "${name}:" "$count"
done

cd ..
