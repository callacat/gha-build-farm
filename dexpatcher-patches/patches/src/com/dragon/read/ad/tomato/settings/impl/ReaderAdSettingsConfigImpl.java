package com.dragon.read.ad.tomato.settings.impl;

import lanchon.dexpatcher.annotation.DexAction;
import lanchon.dexpatcher.annotation.DexEdit;
import lanchon.dexpatcher.annotation.DexReplace;

/** 阅读流广告配置 — 关闭阅读中广告 */
@DexEdit(defaultAction = DexAction.IGNORE)
public final class ReaderAdSettingsConfigImpl {

    @DexReplace
    public boolean isReadFlowAd() {
        return false;
    }

    @DexReplace
    public boolean enableRequestWithTimeGap() {
        return false;
    }

    @DexReplace
    public boolean enableLynxViewPreloadOptimize() {
        return false;
    }
}
