package com.dragon.read;

import lanchon.dexpatcher.annotation.DexAction;
import lanchon.dexpatcher.annotation.DexEdit;
import lanchon.dexpatcher.annotation.DexReplace;
import android.app.Application;
import android.widget.Toast;

@DexEdit(defaultAction = DexAction.IGNORE)
public class MuteApplicationStub extends Application {

    @Override
    @DexReplace
    public void onCreate() {
        super.onCreate();
        Toast.makeText(this, "DexPatcher HelloWorld ✓", Toast.LENGTH_LONG).show();
    }
}
