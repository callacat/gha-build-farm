#!/usr/bin/env bash
set -euo pipefail

# GHA ubuntu-22.04 has Android SDK preinstalled
SDK=/usr/local/lib/android/sdk
AJ=$SDK/platforms/android-34/android.jar
BT=$SDK/build-tools/34.0.0

# Use preinstalled SDK or download
if [ ! -f "$AJ" ]; then
  echo "Android SDK not found at $SDK, downloading..."
  SDK=/tmp/android-sdk
  AJ=$SDK/platforms/android-34/android.jar
  BT=$SDK/build-tools/34.0.0
  mkdir -p /tmp/_sdk
  cd /tmp/_sdk
  curl -sL -o t.zip https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip
  unzip -q t.zip
  mkdir -p $SDK/cmdline-tools
  mv cmdline-tools $SDK/cmdline-tools/latest
  yes | $SDK/cmdline-tools/latest/bin/sdkmanager --sdk_root=$SDK "platforms;android-34" "build-tools;34.0.0" >/dev/null 2>&1
  rm -rf /tmp/_sdk
fi
echo "SDK: $SDK"

# Create Xposed stubs
mkdir -p /tmp/stubs/{src,classes,dex,apk/assets}

cat > /tmp/stubs/src/IXposedMod.java << 'X'
package de.robv.android.xposed; public interface IXposedMod {}
X
cat > /tmp/stubs/src/XCallback.java << 'X'
package de.robv.android.xposed.callbacks; public class XCallback {}
X
cat > /tmp/stubs/src/XC_LoadPackage.java << 'X'
package de.robv.android.xposed.callbacks; public class XC_LoadPackage extends XCallback {
  public static class LoadPackageParam { public String packageName; public ClassLoader classLoader; }
}
X
cat > /tmp/stubs/src/XposedBridge.java << 'X'
package de.robv.android.xposed; public class XposedBridge { public static void log(String s) {} }
X
cat > /tmp/stubs/src/XC_MethodHook.java << 'X'
package de.robv.android.xposed; public class XC_MethodHook {
  public static class MethodHookParam { public Object thisObject; public Object[] args; public Object result; public void setResult(Object r) { this.result = r; } }
  public static class Unhook {}
  protected void beforeHookedMethod(MethodHookParam p) throws Throwable {}
  protected void afterHookedMethod(MethodHookParam p) throws Throwable {}
}
X
cat > /tmp/stubs/src/IXposedHookLoadPackage.java << 'X'
package de.robv.android.xposed; import de.robv.android.xposed.callbacks.XC_LoadPackage;
public interface IXposedHookLoadPackage extends IXposedMod { void handleLoadPackage(XC_LoadPackage.LoadPackageParam p) throws Throwable; }
X
cat > /tmp/stubs/src/XposedHelpers.java << 'X'
package de.robv.android.xposed; import java.lang.reflect.*;
public class XposedHelpers {
  public static Class<?> findClass(String c, ClassLoader cl) throws ClassNotFoundException { return Class.forName(c,false,cl); }
  public static void setObjectField(Object o, String f, Object v) { try{findField(o.getClass(),f).set(o,v);}catch(Exception e){throw new RuntimeException(e);} }
  public static Field findField(Class<?> c, String f) { for(Class<?> x=c;x!=null;x=x.getSuperclass()){try{Field r=x.getDeclaredField(f);r.setAccessible(true);return r;}catch(NoSuchFieldException e){}} throw new RuntimeException(new NoSuchFieldException(f+" in "+c)); }
  public static XC_MethodHook.Unhook findAndHookMethod(Class<?> c, String m, Object... a) { return null; }
  public static XC_MethodHook.Unhook findAndHookConstructor(Class<?> c, Object... a) { return null; }
}
X

# Compile stubs → jar
javac -d /tmp/stubs/classes -source 8 -target 8 /tmp/stubs/src/*.java /tmp/stubs/src/XCallback.java
(cd /tmp/stubs/classes && jar cf /tmp/stubs/stubs.jar .)
echo "stubs OK"

# Compile module
javac -d /tmp/stubs/classes -source 8 -target 8 -cp "$AJ:/tmp/stubs/stubs.jar" .github/scripts/fanqie-hook/MainHook.java
echo "javac OK"

# DEX
$BT/d8 --lib $AJ --lib /tmp/stubs/stubs.jar --min-api 26 --output /tmp/stubs/dex /tmp/stubs/classes
echo "d8 OK"

# Package APK
cat > /tmp/stubs/apk/AndroidManifest.xml << 'M'
<?xml version="1.0"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android" package="com.callacat.fanqiehook">
    <application android:label="FanqieClean">
        <meta-data android:name="xposedmodule" android:value="true" />
        <meta-data android:name="xposeddescription" android:value="Clean" />
        <meta-data android:name="xposedminversion" android:value="53" />
    </application>
</manifest>
M
echo "com.callacat.fanqiehook.MainHook" > /tmp/stubs/apk/assets/xposed_init

$BT/aapt2 link -o /tmp/stubs/module-unsigned.apk -I $AJ --manifest /tmp/stubs/apk/AndroidManifest.xml --auto-add-overlay
(cd /tmp/stubs/dex && zip -q /tmp/stubs/module-unsigned.apk classes.dex)
(cd /tmp/stubs/apk && zip -q /tmp/stubs/module-unsigned.apk assets/xposed_init)

keytool -genkey -v -keystore /tmp/stubs/ks.keystore -alias m -storepass a -keypass a -keyalg RSA -keysize 2048 -validity 10000 -dname "CN=M,O=M,C=C" >/dev/null 2>&1
$BT/apksigner sign --ks /tmp/stubs/ks.keystore --ks-pass pass:a --out /tmp/module.apk /tmp/stubs/module-unsigned.apk
echo "Module: $(stat -c%s /tmp/module.apk) bytes"
