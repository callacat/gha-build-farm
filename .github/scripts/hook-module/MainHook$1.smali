.class Lcom/callacat/fanqiehook/MainHook$1;
.super Lde/robv/android/xposed/XC_MethodHook;
.field final synthetic this$0:Lcom/callacat/fanqiehook/MainHook;
.method constructor <init>(Lcom/callacat/fanqiehook/MainHook;)V
    .registers 2
    iput-object p1, p0, Lcom/callacat/fanqiehook/MainHook$1;->this$0:Lcom/callacat/fanqiehook/MainHook;
    invoke-direct {p0}, Lde/robv/android/xposed/XC_MethodHook;-><init>()V
    return-void
.end method
.method protected afterHookedMethod(Lde/robv/android/xposed/XC_MethodHook$MethodHookParam;)V
    .registers 5
    :try_start
    iget-object v0, p1, Lde/robv/android/xposed/XC_MethodHook$MethodHookParam;->thisObject:Ljava/lang/Object;
    const-string v1, "checkSignEnv"
    const-string v2, "{\"pass\":true}"
    invoke-static {v0, v1, v2}, Lde/robv/android/xposed/XposedHelpers;->setObjectField(Ljava/lang/Object;Ljava/lang/String;Ljava/lang/Object;)V
    iget-object v0, p1, Lde/robv/android/xposed/XC_MethodHook$MethodHookParam;->thisObject:Ljava/lang/Object;
    const-string v1, "checkSignResult"
    const-string v2, "1"
    invoke-static {v0, v1, v2}, Lde/robv/android/xposed/XposedHelpers;->setObjectField(Ljava/lang/Object;Ljava/lang/String;Ljava/lang/Object;)V
    :try_end
    .catchall {:try_start .. :try_end} :return
    :return
    return-void
.end method
