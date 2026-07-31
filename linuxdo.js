// ==UserScript==
// @name linux.do看帖懒人神器
// @namespace https://github.com/callacat
// @version 1.8.0
// @description 自动滚动浏览linux.do帖子，到底自动点击下一个帖子
// @author callacat
// @match https://linux.do/t/*
// @run-at document-idle
// @icon https://linux.do/uploads/default/optimized/1X/3a18b4b0da3e8cf96f7eea15241c3d251f28a39b_2_180x180.png
// @grant none
// @license MIT
// @downloadURL https://raw.githubusercontent.com/callacat/gha-build-farm/main/linuxdo.js
// @updateURL https://raw.githubusercontent.com/callacat/gha-build-farm/main/linuxdo.js
// ==/UserScript==
(function() {
'use strict';

// ===== 可调参数 =====
const SCROLL_STEP = 300;      // 每次滚动像素
const SCROLL_INTERVAL = 1500; // 滚动间隔 ms
const RETRY_INTERVAL = 3000;  // heartbeat 重试间隔 ms
const LAZY_WAIT_MS = 8000;    // 初次滚到底后等待懒加载的最大时间
const LAZY_RETRY_MS = 1000;   // 等待期间重新滚到底的间隔 ms
const BOTTOM_TOLERANCE = 100; // 距底部容差 px
// ===================

let scrollTimer = null;
let lazyWaitTimer = null;
let lazyRetryTimer = null;
let atBottom = false;
let isWaiting = false;
let lastClicked = '';
let firstBottom = 0;

// ============ 辅助函数 ============

function currentTopicId() {
  const m = window.location.pathname.match(/\/t\/[^/]+\/(\d+)/);
  return m ? m[1] : null;
}

function currentPostNumber() {
  const hashMatch = window.location.hash.match(/^#post_(\d+)/);
  if (hashMatch) return Number(hashMatch[1]);
  const el = document.querySelector('article[data-post-number].highlighted');
  if (el) {
    const n = el.getAttribute('data-post-number');
    if (n) return Number(n);
  }
  return null;
}

/** 强制滚到页面绝对底部 */
function scrollToBottom() {
  const max = Math.max(
    document.documentElement.scrollHeight,
    document.body.scrollHeight,
    document.body.offsetHeight
  );
  window.scrollTo(0, max);
}

function isPageBottom() {
  const max = Math.max(
    document.documentElement.scrollHeight,
    document.body.scrollHeight,
    document.body.offsetHeight
  );
  return window.innerHeight + window.scrollY + BOTTOM_TOLERANCE >= max;
}

// ------------ 清理等待状态 ------------

function clearWaiting() {
  if (lazyWaitTimer) { clearTimeout(lazyWaitTimer); lazyWaitTimer = null; }
  if (lazyRetryTimer) { clearInterval(lazyRetryTimer); lazyRetryTimer = null; }
  isWaiting = false;
  firstBottom = 0;
}

// ------------ 核心：点击下一个帖子 ------------

function clickNextTopic() {
  const curId = currentTopicId();
  const curPost = currentPostNumber();
  const links = document.querySelectorAll('a[href*="/t/"]');

  let crossCandidate = null;
  let laterCandidate = null;

  for (const link of links) {
    // 跳过导航区、面包屑、时间线等
    if (link.closest('nav, .breadcrumbs, .select-kit, .timeline-container, .topic-timeline, header, footer')) continue;
    // 跳过隐藏元素
    if (link.offsetParent === null) continue;

    const href = link.getAttribute('href');
    if (!href) continue;

    const m = href.match(/\/t\/[^/]+\/(\d+)(?:\/(\d+))?/);
    if (!m) continue;

    // 防止重复点击同一链接
    if (href === lastClicked) continue;

    const topicId = m[1];
    const postNum = m[2] ? Number(m[2]) : null;

    if (topicId === curId) {
      // 同话题但楼层更靠后 → 备选
      if (postNum && curPost && postNum > curPost && !laterCandidate) {
        laterCandidate = { link, href, postNum };
      }
      continue;
    }

    // 不同话题 → 优先候选（取 DOM 顺序第一个）
    if (!crossCandidate) {
      crossCandidate = { link, href, topicId };
    }
  }

  // 优先级 1: 不同话题
  if (crossCandidate) {
    atBottom = false;
    lastClicked = crossCandidate.href;
    crossCandidate.link.click();
    return;
  }

  // 优先级 2: 同话题更后的楼层（避免完全卡死）
  if (laterCandidate) {
    atBottom = false;
    lastClicked = laterCandidate.href;
    laterCandidate.link.click();
    return;
  }

  // 无可选链接 → heartbeat 会重试
  console.warn('[linux.do懒人] 找不到下一个 topic 链接');
}

// ------------ 滚动主循环 ------------

function doScroll() {
  scrollTimer = null;

  if (!isPageBottom()) {
    // 没到底 → 继续滚动
    atBottom = false;
    clearWaiting();
    window.scrollBy(0, SCROLL_STEP);
    scrollTimer = setTimeout(doScroll, SCROLL_INTERVAL);
    return;
  }

  // ====== 到底逻辑 ======
  // 强制滚动到绝对底部，确保触发 Discourse 懒加载
  scrollToBottom();

  if (!isWaiting) {
    // 初次到底 → 开启等待模式，在此期间不断重试滚动触发懒加载
    isWaiting = true;
    firstBottom = Date.now();
    atBottom = true;

    // 主超时：最终放弃等待，直接尝试点击
    lazyWaitTimer = setTimeout(() => {
      clearWaiting();
      atBottom = true;
      clickNextTopic();
    }, LAZY_WAIT_MS);

    // 重试定时：每隔一段时间重新滚到底
    lazyRetryTimer = setInterval(() => {
      const prevHeight = document.documentElement.scrollHeight;
      scrollToBottom();
      const newHeight = document.documentElement.scrollHeight;

      // 如果高度显著增长，说明懒加载出现了
      if (newHeight > prevHeight + 200) {
        clearWaiting();
        atBottom = true;
        // 给 DOM 一点渲染时间再点击
        setTimeout(clickNextTopic, 1500);
        return;
      }

      // 如果超过总等待时间，放弃等待
      if (Date.now() - firstBottom >= LAZY_WAIT_MS) {
        clearWaiting();
        atBottom = true;
        clickNextTopic();
      }
    }, LAZY_RETRY_MS);
  }
}

// ------------ 触发入口 ------------

function tryScroll() {
  if (scrollTimer) return;
  if (isWaiting) return;
  doScroll();
}

function heartbeat() {
  if (atBottom && !isWaiting) clickNextTopic();
}

// ------------ 启动 ------------

const observer = new MutationObserver(tryScroll);
observer.observe(document.body, { childList: true, subtree: true });
setInterval(heartbeat, RETRY_INTERVAL);
tryScroll();

})();
