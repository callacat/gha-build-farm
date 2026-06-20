#!/usr/bin/env bash
set -euo pipefail

SRC=.github/scripts/hook-module
[ -d "$SRC" ] || { echo "No $SRC dir"; exit 1; }

MD=/tmp/_m
rm -rf "$MD"
mkdir -p "$MD"/smali/com/callacat/fanqiehook
mkdir -p "$MD"/smali/de/robv/android/xposed/callbacks
mkdir -p "$MD"/assets

# Copy hook smali
cp "$SRC/MainHook.smali" "$MD/smali/com/callacat/fanqiehook/"
cp "$SRC/MainHook$1.smali" "$MD/smali/com/callacat/fanqiehook/"

# Copy stubs
cp "$SRC/stubs/de/robv/android/xposed/"*.smali "$MD/smali/de/robv/android/xposed/"
cp "$SRC/stubs/de/robv/android/xposed/callbacks/"*.smali "$MD/smali/de/robv/android/xposed/callbacks/"

# Copy manifest + config
cp "$SRC/AndroidManifest.xml" "$MD/"
cp "$SRC/apktool.yml" "$MD/"
cp "$SRC/xposed_init" "$MD/assets/"

# Download apktool if needed
APKTOOL_JAR=/tmp/apktool.jar
if [ ! -f "$APKTOOL_JAR" ]; then
  curl -sL -o "$APKTOOL_JAR" \
    "https://github.com/iBotPeaches/Apktool/releases/download/v3.0.2/apktool_3.0.2.jar"
fi

java -jar "$APKTOOL_JAR" b "$MD" -o /tmp/module.apk 2>&1
echo "Module: $(stat -c%s /tmp/module.apk) bytes"
