#!/usr/bin/env node
/**
 * hg-mod-pipeline — 红果短剧 APK 修改 Workflow 脚本
 *
 * 用途：封装 hg-mod.yml 的三个 workflow 路径，每次跑完自动更新 BUILD_STATE
 *
 * 用法：
 *   node hg-mod-pipeline.js analysis   [version]
 *   node hg-mod-pipeline.js remove-ads [version]
 *   node hg-mod-pipeline.js patch      [version]
 *   node hg-mod-pipeline.js status     [run-id]
 *
 * 每个命令触发后等待完成，自动检查结果，更新 BUILD_STATE.json
 */
const { execSync } = require("child_process")
const path = require("path")
const fs = require("fs")

const REPO = "callacat/gha-build-farm"
const APP_ID = "hg"
const STATE_FILE = path.join(__dirname, "..", "BUILD_STATE.json")

function sh(cmd) {
  try {
    return execSync(cmd, { encoding: "utf-8", timeout: 300_000 }).trim()
  } catch (e) {
    console.error(`[ERROR] ${cmd}`)
    console.error(e.stderr?.trim() || e.message)
    return null
  }
}

function loadState() {
  try {
    return JSON.parse(fs.readFileSync(STATE_FILE, "utf-8"))
  } catch {
    return { latest_remove_ads: null, latest_patch: null, last_analysis: null }
  }
}

function saveState(state) {
  fs.writeFileSync(STATE_FILE, JSON.stringify(state, null, 2) + "\n")
}

function getApkUrl(version) {
  return `https://github.com/${REPO}/releases/download/hg-original-${version}/hg.apk`
}

async function triggerAndWait(workflow, version) {
  const apkUrl = getApkUrl(version)
  console.log(`📦 Triggering ${workflow} for v${version}...`)
  const result = sh(
    `gh workflow run hg-mod.yml -R ${REPO} -f app_id=${APP_ID} -f apk_url="${apkUrl}" -f workflow=${workflow}`
  )
  if (!result) return null

  // Wait 3s for the run to appear
  await new Promise((r) => setTimeout(r, 3000))

  // Get run ID
  const runInfo = sh(
    `gh run list -R ${REPO} -w hg-mod.yml -L 1 --json databaseId,status --jq '.[0]'`
  )
  if (!runInfo) return null

  const { databaseId, status } = JSON.parse(runInfo)
  console.log(`  Run #${databaseId} (${status})`)

  // Poll until completion
  let attempts = 0
  const maxAttempts = 30 // 10 minutes max
  while (attempts < maxAttempts) {
    await new Promise((r) => setTimeout(r, 20_000))
    const output = sh(
      `gh run view ${databaseId} -R ${REPO} --json conclusion,status --jq '{conclusion,status}'`
    )
    if (!output) break
    const state = JSON.parse(output)
    if (state.status === "completed") {
      console.log(`  ✅ ${workflow} #${databaseId}: ${state.conclusion}`)
      return { runId: databaseId, conclusion: state.conclusion, version }
    }
    attempts++
  }

  console.log(`  ⏳ ${workflow} #${databaseId}: still running after ${maxAttempts} checks`)
  return { runId: databaseId, conclusion: "timeout", version }
}

async function main() {
  const [cmd, arg] = process.argv.slice(2)

  if (!cmd) {
    console.log(`
Usage:
  node hg-mod-pipeline.js analysis <version>     — 分析指定版本
  node hg-mod-pipeline.js remove-ads <version>   — 构建去广告版
  node hg-mod-pipeline.js patch <version>        — 构建去弹窗版
  node hg-mod-pipeline.js status [run-id]        — 查看构建状态
  node hg-mod-pipeline.js list                   — 列出最近运行
`)
    return
  }

  if (cmd === "list") {
    const output = sh(
      `gh run list -R ${REPO} -w hg-mod.yml -L 5 --json databaseId,displayTitle,conclusion,status --jq '.[] | "\(.databaseId) \(.displayTitle) \(.status) \(.conclusion)"'`
    )
    console.log(output || "(none)")
    return
  }

  if (cmd === "status") {
    const runId = arg
    if (runId) {
      const output = sh(
        `gh run view ${runId} -R ${REPO} --json conclusion,status,url --jq '{conclusion,status,url}'`
      )
      console.log(output || "Not found")
    } else {
      const state = loadState()
      console.log(JSON.stringify(state, null, 2))
    }
    return
  }

  if (!["analysis", "remove-ads", "patch"].includes(cmd)) {
    console.error(`Unknown command: ${cmd}`)
    process.exit(1)
  }

  if (!arg) {
    console.error(`Missing version argument`)
    process.exit(1)
  }

  const state = loadState()
  const result = await triggerAndWait(cmd, arg)

  if (!result) {
    console.error("❌ Failed to trigger workflow")
    process.exit(1)
  }

  // Update state
  if (cmd === "remove-ads") {
    state.latest_remove_ads = result
  } else if (cmd === "patch") {
    state.latest_patch = result
  } else if (cmd === "analysis") {
    state.last_analysis = result
  }
  saveState(state)

  // Output download links
  if (result.conclusion === "success" && cmd !== "analysis") {
    const prefix = cmd === "remove-ads" ? "hg-remove-ads" : "hg-patch"
    console.log(`\n✅ Download:`)
    console.log(`  https://github.com/${REPO}/releases/download/${prefix}-latest/${prefix}-${arg}-b${result.runId}.apk`)
    console.log(`  https://gh-proxy.com/https://github.com/${REPO}/releases/download/${prefix}-latest/${prefix}-${arg}-b${result.runId}.apk`)
  }

  if (result.conclusion !== "success") {
    process.exitCode = 1
  }
}

main().catch((e) => {
  console.error(e)
  process.exit(1)
})
