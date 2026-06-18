# gha-build-farm

GitHub Actions 构建农场 — 为老旧/特殊 CPU、自定义架构、或任何需要自由构建的场景提供远程编译能力。

## 问题

本地 CPU（如 J4125）缺 AVX 指令集，预编译的 PyPI wheel / Docker 镜像 Illegal Instruction。
本地从源码编译又慢又缺工具链。

## 方案

把所有"重构建"推到 GitHub Actions 上跑：

```
你 → 触发 workflow → GHA 16 核编译 → 下载制品
```

## Workflow 一览

| Workflow | 功能 | 触发 |
|----------|------|------|
| `build-python-wheel` | 从 PyPI 源码编译 Python wheel（自定义 CFLAGS/架构） | workflow_dispatch + CLI |
| `build-docker` | 构建 Docker 镜像并推送到 GHCR | workflow_dispatch + CLI |
| `build-apt-package` | 从 apt 源码包构建 .deb（指定架构/指令集开关） | workflow_dispatch |
| `build-reverse-tool` | 编译安全/逆向工具（pentestswarm、anything-analyzer 等） | workflow_dispatch + [reverse-skill 自动调度](https://github.com/zhaoxuya520/reverse-skill) |

## 与 reverse-skill 集成

[reverse-skill](https://github.com/zhaoxuya520/reverse-skill) 的安全工具安装流程中，**重量工具默认走 GHA**：

1. `bootstrap-reverse.sh` 检测到需要 `pentestswarm` / `anything-analyzer` 等工具
2. 调用 `skills/scripts/gha-build.sh` → dispatch `build-reverse-tool.yml`
3. GHA 16 核 runner 编译完成后 upload artifact
4. 本机 poll 状态 → download → 安装到 `~/.local/bin/`
5. GHA 不可用时自动 fallback 到本地安装

```
.--------------.     dispatch      .-------------------.
| J4125 (本机)  | ──────────────→ | GHA 16 核 runner  |
| gha-build.sh  |                  | build-reverse-tool |
| poll ↓        |                  | compile Go/Docker  |
| download ←─── | ←── artifact ── | .build-scripts/    |
'--------------'                  '-------------------'
```

## 快速使用

```bash
# 构建一个无 AVX 的 faiss-cpu wheel
gh workflow run build-python-wheel.yml \
  -R callacat/gha-build-farm \
  -f package=faiss-cpu \
  -f version=1.14.2 \
  -f cflags="-mno-avx -mno-avx2"

# 查看运行状态
gh run list -R callacat/gha-build-farm

# 下载产物到当前目录
gh run download <run-id> -R callacat/gha-build-farm
```

## 仓库结构

```
.github/workflows/       ← 所有 workflow 定义
.build-scripts/           ← 每个工具的独立编译脚本
scripts/                 ← 辅助脚本
```
