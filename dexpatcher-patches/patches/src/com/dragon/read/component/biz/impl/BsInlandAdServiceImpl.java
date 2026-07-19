package com.dragon.read.component.biz.impl;

import lanchon.dexpatcher.annotation.DexAction;
import lanchon.dexpatcher.annotation.DexEdit;
import lanchon.dexpatcher.annotation.DexReplace;

/** 国内广告可用性开关 — 返回 false 关掉主要广告源 */
@DexEdit(defaultAction = DexAction.IGNORE)
public final class BsInlandAdServiceImpl {

    @DexReplace
    public boolean isAvailable() {
        return false;
    }
}
