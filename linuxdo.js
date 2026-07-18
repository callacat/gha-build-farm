// ==UserScript==
// @name         linux.do看帖懒人神器
// @namespace    https://github.com/callacat
// @version      1.7.0
// @description  自动滚动浏览linux.do帖子，到底自动点击下一个帖子
// @author       callacat
// @match        https://linux.do/t/*
// @run-at       document-idle
// @iconhttps://linux.do/uploads/default/optimized/1X/3a18b4b0da3e8cf96f7eea15241c3d251f28a39b_2_180x180.png
// @grant        none
// @license      MIT
// @downloadURL https://raw.githubusercontent.com/callacat/gha-build-farm/main/linuxdo.js
// @updateURL https://raw.githubusercontent.com/callacat/gha-build-farm/main/linuxdo.js
// ==/UserScript==

(function() {
    'use strict';

    // ===== 可调参数 =====
    const SCROLL_STEP = 300;
    const SCROLL_INTERVAL = 1500;
    const RETRY_INTERVAL = 3000;
    // ===================

    let scrollTimer = null;
    let atBottom = false;

    // 从 URL 提取当前 topic ID：/t/slug/ID
    function currentTopicId() {
        const m = window.location.pathname.match(/\/t\/[^/]+\/(\d+)/);
        return m ? m[1] : null;
    }

    function clickNextTopic() {
        const curId = currentTopicId();
        // 找所有指向其他 topic 的链接，跳过导航、面包屑、时间线和不可见的链接
        const links = document.querySelectorAll('a[href*="/t/"]');
        for (const link of links) {
            if (link.closest('nav, .breadcrumbs, .select-kit, .timeline-container, .topic-timeline')) continue;
            if (link.offsetParent === null) continue;  // 隐藏元素跳過
            const href = link.getAttribute('href');
            if (!href) continue;
            const m = href.match(/\/t\/[^/]+\/(\d+)/);
            if (!m || m[1] === curId) continue;   // 不是 topic 链接或指向当前页
            atBottom = false;
            link.click();
            return;
        }
        // 无匹配链接时打日志，方便排查
        console.warn('[linux.do懒人] 找不到下一个 topic 链接');
    }

    function doScroll() {
        scrollTimer = null;
        // ponytail: documentElement.scrollHeight 比 body.offsetHeight 更可靠
        const maxScroll = Math.max(
            document.documentElement.scrollHeight,
            document.body.scrollHeight,
            document.body.offsetHeight
        );
        const isBottom = window.innerHeight + window.scrollY + 50 >= maxScroll;
        if (!isBottom) {
            atBottom = false;
            window.scrollBy(0, SCROLL_STEP);
            scrollTimer = setTimeout(doScroll, SCROLL_INTERVAL);
        } else {
            atBottom = true;
            clickNextTopic();
        }
    }

    function tryScroll() {
        if (scrollTimer) return;
        doScroll();
    }

    function heartbeat() {
        if (atBottom) clickNextTopic();
    }

    const observer = new MutationObserver(tryScroll);
    observer.observe(document.body, { childList: true, subtree: true });

    setInterval(heartbeat, RETRY_INTERVAL);
    tryScroll();
})();
