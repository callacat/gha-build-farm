// ==UserScript==
// @name         linux.do看帖懒人神器
// @namespace
// @version      1.6.0
// @description  帮你点开新帖子，帮你从上到下滑动，帮你选择下一个看的帖子。
// @author
// @match        https://linux.do/*
// @icon         https://linux.do/uploads/default/optimized/1X/3a18b4b0da3e8cf96f7eea15241c3d251f28a39b_2_180x180.png
// @grant        none
// @license      MIT
// @downloadURL https://raw.githubusercontent.com/callacat/gha-build-farm/main/linuxdo.js
// @updateURL https://raw.githubusercontent.com/callacat/gha-build-farm/main/linuxdo.js
// ==/UserScript==

(function() {
    'use strict';

    // ===== 可调参数（改这里控制滚动速度） =====
    const SCROLL_STEP = 300;        // 每次滚动像素数，越小越慢
    const SCROLL_INTERVAL = 1500;   // 滚动间隔(毫秒)，越大越慢
    const RELOAD_DELAY = 10000;     // 加载失败后等待(毫秒)
    const RETRY_INTERVAL = 3000;    // 到底后重试点击间隔(毫秒)
    // =====================================

    let scrollTimer = null;
    let atBottom = false;

    function clickRandomTitle() {
        // ponytail: 列表页用精确 class, 话题页推荐区用 href 兜底
        let links = document.querySelectorAll('a.title.raw-link.raw-topic-link, a[href*="/t/topic/"]');
        if (links.length === 0) {
            links = document.querySelectorAll('a[href*="/t/"]');
        }
        for (const link of links) {
            if (link.closest('nav, .breadcrumbs, .select-kit')) continue;
            atBottom = false;
            link.click();
            return;
        }
    }

    function doScroll() {
        scrollTimer = null;

        const isBottom = window.innerHeight + window.scrollY >= document.body.offsetHeight;
        if (!isBottom) {
            atBottom = false;
            window.scrollBy(0, SCROLL_STEP);
            scrollTimer = setTimeout(doScroll, SCROLL_INTERVAL);
        } else {
            atBottom = true;
            clickRandomTitle();
        }
    }

    // ponytail: 共享 timer guard — MO 或心跳都不会打断正在进行的滚动链.
    // 滚动到底后 atBottom=true, 不再创建新 timer.
    function tryScroll() {
        if (scrollTimer) return;
        doScroll();
    }

    function heartbeat() {
        // ponytail: 话题页 DOM 稳定后 MO 不触发, 心跳保证到底后重试点击
        if (atBottom) clickRandomTitle();
    }

    const observer = new MutationObserver(tryScroll);
    observer.observe(document.body, { childList: true, subtree: true });

    setInterval(heartbeat, RETRY_INTERVAL);
    tryScroll();

})();
