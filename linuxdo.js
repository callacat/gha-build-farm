// ==UserScript==
// @name         linux.do看帖懒人神器
// @namespace
// @version      1.5.0
// @description  帮你点开新帖子，帮你从上到下滑动，帮你选择下一个看的帖子。
// @author
// @match        https://linux.do/*
// @icon         https://linux.do/uploads/default/optimized/1X/3a18b4b0da3e8cf96f7eea15241c3d251f28a39b_2_180x180.png
// @grant        none
// @license      MIT
// @downloadURL https://update.greasyfork.org/scripts/489607/linuxdo%E7%9C%8B%E5%B8%96%E6%87%92%E4%BA%BA%E7%A5%9E%E5%99%A8.user.js
// @updateURL https://update.greasyfork.org/scripts/489607/linuxdo%E7%9C%8B%E5%B8%96%E6%87%92%E4%BA%BA%E7%A5%9E%E5%99%A8.meta.js
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
        const titles = document.getElementsByClassName('title raw-link raw-topic-link');
        if (titles.length > 0) {
            atBottom = false;
            titles[Math.floor(Math.random() * titles.length)].click();
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
