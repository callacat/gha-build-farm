#!/usr/bin/env bash
set -euo pipefail

echo "Building APK..."
java -jar apktool.jar b official_smali -o unsigned.apk

echo "Generating debug keystore..."
keytool -genkey -v -keystore debug.keystore -alias androiddebugkey \
  -storepass android -keypass android -keyalg RSA -keysize 2048 \
  -validity 10000 -dname "CN=Debug, OU=Unknown, O=Unknown, L=Unknown, ST=Unknown, C=US"

echo "Signing..."
apksigner sign --ks debug.keystore --ks-pass pass:android \
  --ks-key-alias androiddebugkey --out patched.apk unsigned.apk

echo "Verifying signature..."
apksigner verify --print-certs patched.apk

ls -lh patched.apk
