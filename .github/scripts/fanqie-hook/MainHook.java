package com.callacat.fanqiehook;

import android.app.Activity;
import android.os.Bundle;
import android.view.View;
import android.view.ViewGroup;
import de.robv.android.xposed.IXposedHookLoadPackage;
import de.robv.android.xposed.XC_MethodHook;
import de.robv.android.xposed.XposedBridge;
import de.robv.android.xposed.XposedHelpers;
import de.robv.android.xposed.callbacks.XC_LoadPackage;

public class MainHook implements IXposedHookLoadPackage {
    @Override
    public void handleLoadPackage(XC_LoadPackage.LoadPackageParam lpparam) {
        if (!lpparam.packageName.equals("com.dragon.read")) return;
        hookCheckSign(lpparam, "com.dragon.read.rpc.model.NovelCommonParam");
        hookCheckSign(lpparam, "com.dragon.read.saas.ugc.model.NovelCommonParam");
        for (String c : new String[]{
            "com.dragon.read.rpc.model.AntiCheatParam",
            "com.dragon.read.saas.rpc.model.AntiCheatParam",
            "com.bytedance.rpc.model.AntiCheatParam",
        }) hookSignRes(lpparam, c);
        hookSignRes(lpparam, "com.dragon.read.rpc.model.HeaderArgs");
        hookField(lpparam, "com.dragon.read.rpc.model.HeaderArgs", "checkSignResV2", "1");
        XposedHelpers.findAndHookMethod(ViewGroup.class, "addView", View.class,
            new XC_MethodHook() {
                @Override protected void beforeHookedMethod(MethodHookParam param) {
                    View v = (View) param.args[0];
                    if (v != null) {
                        String n = v.getClass().getName().toLowerCase();
                        if (n.contains("adview") || n.contains("nativead") || n.contains("banner"))
                            param.setResult(null);
                    }
                }
            });
        XposedHelpers.findAndHookMethod(Activity.class, "onCreate", Bundle.class,
            new XC_MethodHook() {
                @Override protected void afterHookedMethod(MethodHookParam param) {
                    Activity a = (Activity) param.thisObject;
                    String n = a.getClass().getName();
                    if (n.contains("Splash") || n.contains("AdActivity"))
                        a.finish();
                }
            });
        XposedBridge.log("FanqieHook: active");
    }
    void hookCheckSign(XC_LoadPackage.LoadPackageParam p, String cls) {
        try { Class<?> c = p.classLoader.loadClass(cls);
            XposedHelpers.findAndHookConstructor(c, new XC_MethodHook() {
                @Override protected void afterHookedMethod(MethodHookParam param) {
                    try { XposedHelpers.setObjectField(param.thisObject, "checkSignEnv", "{\"pass\":true}"); } catch (Throwable t) {}
                    try { XposedHelpers.setObjectField(param.thisObject, "checkSignResult", "1"); } catch (Throwable t) {}
                }
            });
        } catch (Throwable t) { XposedBridge.log("FanqieHook: no " + cls); }
    }
    void hookSignRes(XC_LoadPackage.LoadPackageParam p, String cls) {
        try { Class<?> c = p.classLoader.loadClass(cls);
            XposedHelpers.findAndHookConstructor(c, new XC_MethodHook() {
                @Override protected void afterHookedMethod(MethodHookParam param) {
                    try { XposedHelpers.setObjectField(param.thisObject, "checkSignRes", "1"); } catch (Throwable t) {}
                }
            });
        } catch (Throwable t) {}
    }
    void hookField(XC_LoadPackage.LoadPackageParam p, String cls, String f, Object v) {
        try { Class<?> c = p.classLoader.loadClass(cls);
            XposedHelpers.findAndHookConstructor(c, new XC_MethodHook() {
                @Override protected void afterHookedMethod(MethodHookParam param) {
                    try { XposedHelpers.setObjectField(param.thisObject, f, v); } catch (Throwable t) {}
                }
            });
        } catch (Throwable t) {}
    }
}
