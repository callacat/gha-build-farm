.class public Lcom/callacat/fanqiehook/MainHook;
.super Ljava/lang/Object;
.implements Lde/robv/android/xposed/IXposedHookLoadPackage;
.method public constructor <init>()V
    .registers 1
    invoke-direct {p0}, Ljava/lang/Object;-><init>()V
    return-void
.end method
.method public handleLoadPackage(Lde/robv/android/xposed/callbacks/XC_LoadPackage$LoadPackageParam;)V
    .registers 5
    iget-object v0, p1, Lde/robv/android/xposed/callbacks/XC_LoadPackage$LoadPackageParam;->packageName:Ljava/lang/String;
    const-string v1, "com.dragon.read"
    invoke-virtual {v0, v1}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z
    move-result v0
    if-nez v0, :ret
    :try_start
    iget-object v0, p1, Lde/robv/android/xposed/callbacks/XC_LoadPackage$LoadPackageParam;->classLoader:Ljava/lang/ClassLoader;
    const-string v1, "com.dragon.read.rpc.model.NovelCommonParam"
    invoke-static {v1, v0}, Lde/robv/android/xposed/XposedHelpers;->findClass(Ljava/lang/String;Ljava/lang/ClassLoader;)Ljava/lang/Class;
    move-result-object v0
    const/4 v1, 0x0
    new-array v1, v1, [Ljava/lang/Class;
    new-instance v2, Lcom/callacat/fanqiehook/MainHook$1;
    invoke-direct {v2, p0}, Lcom/callacat/fanqiehook/MainHook$1;-><init>(Lcom/callacat/fanqiehook/MainHook;)V
    invoke-static {v0, v1, v2}, Lde/robv/android/xposed/XposedHelpers;->findAndHookConstructor(Ljava/lang/Class;[Ljava/lang/Object;Lde/robv/android/xposed/XC_MethodHook;)Lde/robv/android/xposed/XC_MethodHook$Unhook;
    :try_end
    .catchall {:try_start .. :try_end} :ret
    :ret
    return-void
.end method
