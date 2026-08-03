#! /bin/bash
# =====================================================================
# run.sh — Plugin/Spider 统一启动入口
#
# 适配三种运行场景：手动 / cron(Linux) / launchd(macOS)
#
# 关键改动（相对旧版）：
#   - 用 BASH_SOURCE 解析项目绝对路径，不再依赖 pwd
#   - 显式 export PATH，解决 launchd/cron 下 PATH 过于精简的问题
#   - 日志路径可由环境变量覆盖，默认 $HOME/Library/Logs/spider (macOS)
#     在 Linux 下建议 export SPIDER_LOG_DIR=/var/log/spider
#   - Poetry 缺失时直接报错退出，不再在定时任务里联网安装
#   - set -euo pipefail，失败立即可见
# =====================================================================

set -euo pipefail

# ---- 1. 解析项目根目录（spider/）--------------------------------------
SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_PATH}/.." && pwd)"

# ---- 2. PATH 环境变量 -------------------------------------------------
# launchd / cron 给的 PATH 通常只有 /usr/bin:/bin，需要补上常见安装位置
export PATH="$HOME/.local/bin:$HOME/.local/share/pypoetry/venv/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

export PYTHONPATH="${PROJECT_DIR}:${PYTHONPATH:-}"

# ---- 2.1 自动探测 Poetry（PATH 找不到时遍历常见安装位置）----------------
POETRY_BIN=""
if command -v poetry >/dev/null 2>&1; then
    POETRY_BIN="$(command -v poetry)"
else
    # 常见 poetry 安装位置（macOS python.org / homebrew / pyenv / linux）
    CANDIDATES=(
        "/Library/Frameworks/Python.framework/Versions/3.11/bin/poetry"
        "/Library/Frameworks/Python.framework/Versions/3.12/bin/poetry"
        "/Library/Frameworks/Python.framework/Versions/3.13/bin/poetry"
        "$HOME/.local/bin/poetry"
        "$HOME/.local/share/pypoetry/venv/bin/poetry"
        "/opt/homebrew/bin/poetry"
        "/usr/local/bin/poetry"
        "/usr/bin/poetry"
    )
    for cand in "${CANDIDATES[@]}"; do
        if [ -x "$cand" ]; then
            POETRY_BIN="$cand"
            # 把该目录加进 PATH，方便后续 poetry run 调用子进程
            export PATH="$(dirname "$cand"):${PATH}"
            break
        fi
    done
fi

# ---- 3. 日志目录（可由环境变量覆盖）------------------------------------
SPIDER_LOG_DIR="${SPIDER_LOG_DIR:-$HOME/Library/Logs/spider}"
mkdir -p "${SPIDER_LOG_DIR}"

OUT_LOG="${SPIDER_LOG_DIR}/spider.out.log"
ERR_LOG="${SPIDER_LOG_DIR}/spider.error.log"
touch "${OUT_LOG}" "${ERR_LOG}"

# ---- 4. 检查 Poetry（缺失则报错退出，不自动联网安装）-------------------
if ! command -v poetry >/dev/null 2>&1; then
    echo "[FATAL] $(date '+%F %T') Poetry 未安装，PATH=${PATH}" | tee -a "${ERR_LOG}" >&2
    echo "请先执行: curl -sSL https://install.python-poetry.org | python3 -" >&2
    exit 127
fi

# ---- 5. 检查虚拟环境，缺失则创建一次 ---------------------------------
if [ ! -d "$(poetry env info --path 2>/dev/null)" ]; then
    echo "[INFO] $(date '+%F %T') Poetry 虚拟环境不存在，执行 poetry install --no-root" | tee -a "${OUT_LOG}"
    (cd "${PROJECT_DIR}" && poetry install --no-root)
fi

# ---- 6. 启动爬虫 ------------------------------------------------------
echo "[INFO] $(date '+%F %T') Starting spider in Poetry environment, dir=${PROJECT_DIR}" | tee -a "${OUT_LOG}"
cd "${PROJECT_DIR}"
exec poetry run python spider/run.py