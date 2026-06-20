#!/usr/bin/env bash
set -euo pipefail

# Find Android SDK (pre-installed on GHA ubuntu-22.04)
SDK=""
for d in /usr/local/lib/android/sdk "$HOME"/android-sdk /opt/android-sdk "$ANDROID_HOME"; do
  [ -n "$d" ] && [ -d "$d" ] && SDK="$d" && break
done

# If no SDK, download one
if [ -z "$SDK" ]; then
  SDK=/tmp/asdk
  mkdir -p /tmp/_dl && cd /tmp/_dl
  curl -sL -o t.zip https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip
  unzip -q t.zip
  mkdir -p "$SDK/cmdline-tools" && mv cmdline-tools "$SDK/cmdline-tools/latest"
  yes | "$SDK/cmdline-tools/latest/bin/sdkmanager" --sdk_root="$SDK" "platforms;android-34" "build-tools;34.0.0" >/dev/null 2>&1
  rm -rf /tmp/_dl
fi

# Find android.jar
AJ=$(find "$SDK/platforms" -name android.jar 2>/dev/null | head -1)
if [ -z "$AJ" ]; then
  cd /tmp && curl -sL -o p.zip https://dl.google.com/android/repository/platform-34_r03.zip
  mkdir -p "$SDK/platforms" && unzip -q p.zip -d "$SDK/platforms/"
  AJ="$SDK/platforms/android-34/android.jar"
fi

# Find build-tools
BT=$(find "$SDK/build-tools" -name d8 2>/dev/null | head -1 | xargs dirname)
if [ -z "$BT" ]; then
  echo "No build-tools found"; exit 1
fi

echo "SDK=$SDK AJ=$AJ BT=$BT"

# Create stubs
MD=/tmp/_m; rm -rf "$MD"
mkdir -p "$MD"/{s,classes,dex,apk/assets}

for pkg in de/robv/android/xposed de/robv/android/xposed/callbacks; do
  mkdir -p "$MD/s/$pkg"
done

cat > "$MD/s/de/robv/android/xposed/IXposedMod.java" << 'E'
package de.robv.android.xposed;
public interface IXposedMod {}
E

cat > "$MD/s/de/robv/android/xposed/callbacks/XCallback.java" << 'E'
package de.robv.android.xposed.callbacks;
public class XCallback {}
E

cat > "$MD/s/de/robv/android/xposed/callbacks/XC_LoadPackage.java" << 'E'
package de.robv.android.xposed.callbacks;
public class XC_LoadPackage extends XCallback {
  public static class LoadPackageParam {
    public String packageName;
    public ClassLoader classLoader;
  }
}
E

cat > "$MD/s/de/robv/android/xposed/XposedBridge.java" << 'E'
package de.robv.android.xposed;
public class XposedBridge { public static void log(String s) {} }
E

cat > "$MD/s/de/robv/android/xposed/XC_MethodHook.java" << 'E'
package de.robv.android.xposed;
public class XC_MethodHook {
  public static class MethodHookParam {
    public Object thisObject; public Object[] args; public Object result;
    public void setResult(Object r) { this.result = r; }
  }
  public static class Unhook {}
  protected void beforeHookedMethod(MethodHookParam p) throws Throwable {}
  protected void afterHookedMethod(MethodHookParam p) throws Throwable {}
}
E

cat > "$MD/s/de/robv/android/xposed/IXposedHookLoadPackage.java" << 'E'
package de.robv.android.xposed;
import de.robv.android.xposed.callbacks.XC_LoadPackage;
public interface IXposedHookLoadPackage extends IXposedMod {
  void handleLoadPackage(XC_LoadPackage.LoadPackageParam lpparam) throws Throwable;
}
E

cat > "$MD/s/de/robv/android/xposed/XposedHelpers.java" << 'E'
package de.robv.android.xposed;
import java.lang.reflect.*;
public class XposedHelpers {
  public static Class<?> findClass(String c, ClassLoader cl) throws ClassNotFoundException { return Class.forName(c,false,cl); }
  public static void setObjectField(Object o, String f, Object v) { try{findField(o.getClass(),f).set(o,v);}catch(Exception e){throw new RuntimeException(e);} }
  public static Field findField(Class<?> c, String f) { for(Class<?> x=c;x!=null;x=x.getSuperclass()){try{Field r=x.getDeclaredField(f);r.setAccessible(true);return r;}catch(NoSuchFieldException e){}} throw new RuntimeException(new NoSuchFieldException(f+" in "+c)); }
  public static XC_MethodHook.Unhook findAndHookMethod(Class<?> c, String m, Object... a) { return null; }
  public static XC_MethodHook.Unhook findAndHookConstructor(Class<?> c, Object... a) { return null; }
}
E

# Compile stubs → jar
javac -d "$MD/classes" -source 8 -target 8 "$MD/s"/de/robv/android/xposed/*.java "$MD/s"/de/robv/android/xposed/callbacks/*.java
(cd "$MD/classes" && jar cf "$MD/stubs.jar" .)

# Compile module java → class
javac -d "$MD/classes" -source 8 -target 8 -cp "$AJ:$MD/stubs.jar" .github/scripts/fanqie-hook/MainHook.java
echo "javac OK"

# class → dex
"$BT/d8" --lib "$AJ" --lib "$MD/stubs.jar" --min-api 26 --output "$MD/dex" $(find "$MD/classes" -name '*.class' | grep -v 'de/robv')
echo "d8 OK"
ls -la "$MD/dex/"

# Build APK with aapt2
cat > "$MD/apk/AndroidManifest.xml" << 'M'
<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android" package="com.callacat.fanqiehook">
    <application android:label="FanqieClean">
        <meta-data android:name="xposedmodule" android:value="true" />
        <meta-data android:name="xposeddescription" android:value="番茄小说去广告+去签名检测" />
        <meta-data android:name="xposedminversion" android:value="53" />
    </application>
</manifest>
M
echo "com.callacat.fanqiehook.MainHook" > "$MD/apk/assets/xposed_init"

"$BT/aapt2" link -o "$MD/module.apk" -I "$AJ" --manifest "$MD/apk/AndroidManifest.xml" --auto-add-overlay
(cd "$MD/dex" && zip -q "$MD/module.apk" classes.dex)
(cd "$MD/apk" && zip -q "$MD/module.apk" assets/xposed_init)

# Sign module APK
keytool -genkey -v -keystore "$MD/ks" -alias m -storepass a -keypass a -keyalg RSA -keysize 2048 -validity 10000 -dname "CN=M,O=M,C=C" >/dev/null 2>&1
"$BT/apksigner" sign --ks "$MD/ks" --ks-pass pass:a --out /tmp/module.apk "$MD/module.apk"
echo "Module: $(stat -c%s /tmp/module.apk) bytes"
