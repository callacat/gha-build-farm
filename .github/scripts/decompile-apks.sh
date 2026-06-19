#!/usr/bin/env bash
set -euo pipefail

APKTOOL_JAR=apktool.jar
if [ ! -f "$APKTOOL_JAR" ]; then
  curl -sL -o "$APKTOOL_JAR" \
    https://github.com/iBotPeaches/Apktool/releases/download/v2.11.1/apktool_2.11.1.jar
fi

echo "Decompiling official.apk..."
java -jar "$APKTOOL_JAR" d -f official.apk -o official_smali

echo "Decompiling modded.apk..."
java -jar "$APKTOOL_JAR" d -f modded.apk -o modded_smali

echo "Done"
