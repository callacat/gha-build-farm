#!/usr/bin/env bash
set -euo pipefail
SDK=""
for d in /usr/local/lib/android/sdk "$HOME/android-sdk" /opt/android-sdk "$ANDROID_HOME"; do
  if [ -n "$d" ] && [ -d "$d" ]; then SDK="$d"; break; fi
done
if [ -z "$SDK" ]; then
  SDK=/tmp/android-sdk
  mkdir -p /tmp/_sdk; cd /tmp/_sdk
  curl -sL -o t.zip https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip
  unzip -q t.zip; mkdir -p "$SDK/cmdline-tools"; mv cmdline-tools "$SDK/cmdline-tools/latest"
  yes | "$SDK/cmdline-tools/latest/bin/sdkmanager" --sdk_root="$SDK" "platforms;android-34" "build-tools;34.0.0" >/dev/null 2>&1
  rm -rf /tmp/_sdk
fi
AJ=$(ls "$SDK/platforms"/android-*/android.jar 2>/dev/null | head -1)
if [ -z "$AJ" ]; then
  cd /tmp && curl -sL -o p.zip https://dl.google.com/android/repository/platform-34_r03.zip
  unzip -q p.zip -d "$SDK/platforms/"; AJ="$SDK/platforms/android-34/android.jar"
fi
BT=$(ls -d "$SDK"/build-tools/*/ 2>/dev/null | sort -V | tail -1)
echo "SDK=$SDK AJ=$AJ BT=$BT"
MD=/tmp/_m; rm -rf "$MD"; mkdir -p "$MD"/{s,classes,dex,apk/assets}
cat > "$MD/s/IXposedMod.java" << 'E'
package de.robv.android.xposed; public interface IXposedMod {}
E
cat > "$MD/s/XCallback.java" << 'E'
package de.robv.android.xposed.callbacks; public class XCallback {}
E
cat > "$MD/s/XC_LoadPackage.java" << 'E'
package de.robv.android.xposed.callbacks;
public class XC_LoadPackage extends XCallback {
  public static class LoadPackageParam { public String packageName; public ClassLoader classLoader; }
}
E
cat > "$MD/s/XposedBridge.java" << 'E'
package de.robv.android.xposed; public class XposedBridge { public static void log(String s) {} }
E
cat > "$MD/s/XC_MethodHook.java" << 'E'
package de.robv.android.xposed;
public class XC_MethodHook {
  public static class MethodHookParam { public Object thisObject; public Object[] args; public Object result; public void setResult(Object r) { this.result = r; } }
  public static class Unhook {}
  protected void beforeHookedMethod(MethodHookParam p) throws Throwable {}
  protected void afterHookedMethod(MethodHookParam p) throws Throwable {}
}
E
cat > "$MD/s/IXposedHookLoadPackage.java" << 'E'
package de.robv.android.xposed; import de.robv.android.xposed.callbacks.XC_LoadPackage;
public interface IXposedHookLoadPackage extends IXposedMod { void handleLoadPackage(XC_LoadPackage.LoadPackageParam p) throws Throwable; }
E
cat > "$MD/s/XposedHelpers.java" << 'E'
package de.robv.android.xposed; import java.lang.reflect.*;
public class XposedHelpers {
  public static Class<?> findClass(String c, ClassLoader cl) throws ClassNotFoundException { return Class.forName(c,false,cl); }
  public static void setObjectField(Object o, String f, Object v) { try{findField(o.getClass(),f).set(o,v);}catch(Exception e){throw new RuntimeException(e);} }
  public static Field findField(Class<?> c, String f) { for(Class<?> x=c;x!=null;x=x.getSuperclass()){try{Field r=x.getDeclaredField(f);r.setAccessible(true);return r;}catch(NoSuchFieldException e){}} throw new RuntimeException(new NoSuchFieldException(f+" in "+c)); }
  public static XC_MethodHook.Unhook findAndHookMethod(Class<?> c, String m, Object... a) { return null; }
  public static XC_MethodHook.Unhook findAndHookConstructor(Class<?> c, Object... a) { return null; }
}
E
javac -d "$MD/classes" -source 8 -target 8 "$MD/s"/*.java
(cd "$MD/classes" && jar cf "$MD/stubs.jar" .)
javac -d "$MD/classes" -source 8 -target 8 -cp "$AJ:$MD/stubs.jar" .github/scripts/fanqie-hook/MainHook.java
echo "compile OK"
"$BT/d8" --lib "$AJ" --lib "$MD/stubs.jar" --min-api 26 --output "$MD/dex" "$MD/classes"
echo "d8 OK"
cat > "$MD/apk/AndroidManifest.xml" << 'M'
<?xml version="1.0"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android" package="com.callacat.fanqiehook">
    <application android:label="FanqieClean">
        <meta-data android:name="xposedmodule" android:value="true" />
        <meta-data android:name="xposeddescription" android:value="Clean" />
        <meta-data android:name="xposedminversion" android:value="53" />
    </application>
</manifest>
M
echo "com.callacat.fanqiehook.MainHook" > "$MD/apk/assets/xposed_init"
"$BT/aapt2" link -o "$MD/unsigned.apk" -I "$AJ" --manifest "$MD/apk/AndroidManifest.xml" --auto-add-overlay
(cd "$MD/dex" && zip -q "$MD/unsigned.apk" classes.dex)
(cd "$MD/apk" && zip -q "$MD/unsigned.apk" assets/xposed_init)
keytool -genkey -v -keystore "$MD/ks" -alias m -storepass a -keypass a -keyalg RSA -keysize 2048 -validity 10000 -dname "CN=M,O=M,C=C" >/dev/null 2>&1
"$BT/apksigner" sign --ks "$MD/ks" --ks-pass pass:a --out /tmp/module.apk "$MD/unsigned.apk"
echo "Module: $(stat -c%s /tmp/module.apk) bytes"
