#!/usr/bin/env bash
set -euo pipefail

echo "Building APK..."
java -jar apktool.jar b official_smali -o unsigned.apk
ls -lh unsigned.apk

echo "Signing with jarsigner..."
jarsigner -sigalg SHA1withRSA -digestalg SHA1 \
  -keystore debug.keystore -storepass android \
  unsigned.apk androiddebugkey 2>&1 | tail -3

echo "Verifying..."
jarsigner -verify -keystore debug.keystore unsigned.apk 2>&1 | tail -2

cp unsigned.apk patched.apk
ls -lh patched.apk
echo "SIGNED OK"
