package com.dragon.read;

import lanchon.dexpatcher.annotation.DexAction;
import lanchon.dexpatcher.annotation.DexEdit;
import lanchon.dexpatcher.annotation.DexAdd;
import android.app.Application;
import android.content.Context;
import android.widget.Toast;

@DexEdit(defaultAction = DexAction.IGNORE)
public class MuteApplicationStub extends Application {

    @Override
    @DexAdd
    protected void attachBaseContext(Context base) {
        super.attachBaseContext(base);
        Toast.makeText(this, "DexPatcher HelloWorld ✓", Toast.LENGTH_LONG).show();
    }
}
