package com.dragon.read.ad.reward.impl;

import java.util.List;

import lanchon.dexpatcher.annotation.DexAction;
import lanchon.dexpatcher.annotation.DexEdit;
import lanchon.dexpatcher.annotation.DexReplace;

/** 激励广告 — 返回空数据，不请求广告 */
@DexEdit(defaultAction = DexAction.IGNORE)
public final class HongguoRewardServiceImpl {

    @DexReplace
    public String getRewardAdReportPosition(String str) {
        return "";
    }

    @DexReplace
    public int getTimeOut(String from) {
        return 0;
    }

    @DexReplace
    public int getRit(String from) {
        return 0;
    }

    @DexReplace
    public String getAdFrom(String from) {
        return "";
    }

    @DexReplace
    public boolean isAvailable(String from) {
        return false;
    }

    @DexReplace
    public int getBannerType(String from, String str) {
        return 0;
    }

    @DexReplace
    public String getDarkAdCreatorId(String str, String str2) {
        return "";
    }

    @DexReplace
    public boolean enableAdAliasPositionBackup() {
        return false;
    }

    @DexReplace
    public boolean isAdAliasPositionExistLocal(String str) {
        return false;
    }
}
