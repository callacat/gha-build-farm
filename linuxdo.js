// ==UserScript==
// @name         linux.do看帖懒人神器
// @namespace
// @version      1.4.0
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
    const SCROLL_STEP = 300; // 每次滚动像素数，越小越慢
    const SCROLL_INTERVAL = 1500; // 滚动间隔(毫秒)，越大越慢
    const RELOAD_DELAY = 10000; // 加载失败后等待(毫秒)
    // =====================================

    function waitSomeSeconds() {
        setTimeout(function() {
            console.log('10秒钟已过！');
            window.location.href = "/latest";
        }, RELOAD_DELAY);
    }

    function clickRandomTitle() {
        const titles = document.getElementsByClassName('title raw-link raw-topic-link');
        if (titles.length > 0) {
            const randomIndex = Math.floor(Math.random() * titles.length);
            titles[randomIndex].click();
        } else {
            console.log('No elements found with the specified class names.');
        }
    }

    let scrollTimer = null;
    let atBottom = false;

    function scheduleScroll() {
        // ponytail: 滚动中 guard, 到底后允许 MutationObserver 重置 timer 重试点击.
        if (scrollTimer && !atBottom) return;
        if (scrollTimer) clearTimeout(scrollTimer);
        scrollTimer = setTimeout(tick, SCROLL_INTERVAL);
    }

    function tick() {
        scrollTimer = null;

        const isBottom = window.innerHeight + window.scrollY >= document.body.offsetHeight;
        if (!isBottom) {
            atBottom = false;
            window.scrollBy(0, SCROLL_STEP);
            scheduleScroll();
        } else {
            atBottom = true;
            const dd = '抱歉，我们无法加载该话题，可能是由于连接问题。请重试。如果问题仍然存在，请告诉我们。';
            if (document.body.textContent.includes(dd)) {
                waitSomeSeconds();
            } else {
                clickRandomTitle();
                // ponytail: tick 不自循环, 靠 MutationObserver 在懒加载后触发重试.
            }
        }
    }

    const observer = new MutationObserver(() => {
        if (atBottom) {
            clickRandomTitle(); // 到底后直接重试, 不打扰滚动 timer
        } else {
            scheduleScroll();
        }
    });

    observer.observe(document.body, { childList: true, subtree: true });
    tick();

})();
