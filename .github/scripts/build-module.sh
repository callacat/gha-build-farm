#!/usr/bin/env bash
set -euo pipefail

# Compile Xposed module + sign as APK
# Input:  .github/scripts/fanqie-hook/MainHook.java
# Output: /tmp/module.apk

SDK=/tmp/android-sdk
AJ="$SDK/platforms/android-34/android.jar"
BT="$SDK/build-tools/34.0.0"
SRC=.github/scripts/fanqie-hook/MainHook.java
OUT=/tmp/module-out

# Setup SDK if needed
if [ ! -d "$SDK" ]; then
  mkdir -p /tmp/cmd
  cd /tmp/cmd
  curl -sL -o t.zip https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip
  unzip -q t.zip
  mkdir -p "$SDK/cmdline-tools"
  mv cmdline-tools "$SDK/cmdline-tools/latest"
  yes | "$SDK/cmdline-tools/latest/bin/sdkmanager" \
    --sdk_root="$SDK" "platforms;android-34" "build-tools;34.0.0" > /dev/null 2>&1
  rm -rf /tmp/cmd
  echo "SDK ready"
fi

# Create Xposed stubs
mkdir -p /tmp/stubs/{de/robv/android/xposed/callbacks,out}

cat > /tmp/stubs/de/robv/android/xposed/IXposedMod.java << 'E'
package de.robv.android.xposed; public interface IXposedMod {}
E
cat > /tmp/stubs/de/robv/android/xposed/callbacks/XCallback.java << 'E'
package de.robv.android.xposed.callbacks; public class XCallback {}
E
cat > /tmp/stubs/de/robv/android/xposed/callbacks/XC_LoadPackage.java << 'E'
package de.robv.android.xposed.callbacks;
public class XC_LoadPackage extends XCallback {
  public static class LoadPackageParam { public String packageName; public ClassLoader classLoader; }
}
E
cat > /tmp/stubs/de/robv/android/xposed/XposedBridge.java << 'E'
package de.robv.android.xposed; public class XposedBridge { public static void log(String s) {} }
E
cat > /tmp/stubs/de/robv/android/xposed/XC_MethodHook.java << 'E'
package de.robv.android.xposed;
public class XC_MethodHook {
  public static class MethodHookParam { public Object thisObject; public Object[] args; public Object result; public void setResult(Object r) { this.result = r; } }
  public static class Unhook {}
  protected void beforeHookedMethod(MethodHookParam param) throws Throwable {}
  protected void afterHookedMethod(MethodHookParam param) throws Throwable {}
}
E
cat > /tmp/stubs/de/robv/android/xposed/IXposedHookLoadPackage.java << 'E'
package de.robv.android.xposed;
import de.robv.android.xposed.callbacks.XC_LoadPackage;
public interface IXposedHookLoadPackage extends IXposedMod {
  void handleLoadPackage(XC_LoadPackage.LoadPackageParam lpparam) throws Throwable;
}
E
cat > /tmp/stubs/de/robv/android/xposed/XposedHelpers.java << 'E'
package de.robv.android.xposed;
import java.lang.reflect.*;
public class XposedHelpers {
  public static Class<?> findClass(String c, ClassLoader cl) throws ClassNotFoundException { return Class.forName(c,false,cl); }
  public static void setObjectField(Object o, String f, Object v) {
    try { findField(o.getClass(),f).set(o,v); } catch (Exception e) { throw new RuntimeException(e); }
  }
  public static Field findField(Class<?> c, String f) {
    for (Class<?> x=c; x!=null; x=x.getSuperclass()) {
      try { Field r=x.getDeclaredField(f); r.setAccessible(true); return r; } catch (NoSuchFieldException e) {}
    }
    throw new RuntimeException(new NoSuchFieldException(f+" in "+c));
  }
  public static XC_MethodHook.Unhook findAndHookMethod(Class<?> c, String m, Object... a) { return null; }
  public static XC_MethodHook.Unhook findAndHookConstructor(Class<?> c, Object... a) { return null; }
}
E

# Compile stubs
javac -d /tmp/stubs/out /tmp/stubs/de/robv/android/xposed/*.java /tmp/stubs/de/robv/android/xposed/callbacks/*.java
(cd /tmp/stubs/out && jar cf /tmp/stubs.jar .)

# Compile module
mkdir -p "$OUT/classes"
javac -d "$OUT/classes" -source 8 -target 8 -cp "$AJ:/tmp/stubs.jar" "$SRC"
echo "javac OK"

# DEX
mkdir -p "$OUT/dex"
"$BT/d8" --lib "$AJ" --lib /tmp/stubs.jar --min-api 26 --output "$OUT/dex" "$OUT/classes"
echo "d8 OK"

# Package APK
mkdir -p "$OUT/apk/assets"
echo "com.callacat.fanqiehook.MainHook" > "$OUT/apk/assets/xposed_init"
cat > "$OUT/apk/AndroidManifest.xml" << 'M'
<?xml version="1.0"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android" package="com.callacat.fanqiehook">
    <application android:label="FanqieClean">
        <meta-data android:name="xposedmodule" android:value="true" />
        <meta-data android:name="xposeddescription" android:value="Clean" />
        <meta-data android:name="xposedminversion" android:value="53" />
    </application>
</manifest>
M

"$BT/aapt2" link -o "$OUT/module-unsigned.apk" -I "$AJ" --manifest "$OUT/apk/AndroidManifest.xml" --auto-add-overlay
(cd "$OUT/dex" && zip -q "$OUT/module-unsigned.apk" classes.dex)
(cd "$OUT/apk" && zip -q "$OUT/module-unsigned.apk" assets/xposed_init)

keytool -genkey -v -keystore /tmp/ks.keystore -alias m -storepass a -keypass a \
  -keyalg RSA -keysize 2048 -validity 10000 -dname "CN=M,O=M,C=C" 2>&1
"$BT/apksigner" sign --ks /tmp/ks.keystore --ks-pass pass:a --out /tmp/module.apk "$OUT/module-unsigned.apk"
echo "Module: $(stat -c%s /tmp/module.apk) bytes"
