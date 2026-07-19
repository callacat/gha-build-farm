package com.dragon.read.ad.banner.impl;

import lanchon.dexpatcher.annotation.DexAction;
import lanchon.dexpatcher.annotation.DexEdit;
import lanchon.dexpatcher.annotation.DexReplace;

/** 横幅广告 — 返回空Rit/配置，不再请求广告 */
@DexEdit(defaultAction = DexAction.IGNORE)
public final class HongguoBannerServiceImpl {

    @DexReplace
    public String getRitReadFlow(boolean z17) {
        return "";
    }

    @DexReplace
    public boolean enableShortSeriesAdJoinRevert() {
        return false;
    }
}
