# Spider 定时任务部署文档

> 本文档记录 macOS（launchd）与 Linux（cron）两种定时任务的完整部署过程。
> 实际验证环境：macOS + Python 3.11 + Poetry 1.8.0（位于 `/Library/Frameworks/Python.framework/Versions/3.11/bin/`）。
> 验证时间：2026-08-02 17:52-17:54，四个爬虫全部 `Spider closed (finished)`。

---

## 一、前置条件

| 项目 | 要求 |
|------|------|
| Python | >=3.11, <3.13 |
| Poetry | 已安装并能 `poetry run python spider/run.py` |
| 依赖 | `cd spider && poetry install --no-root` 已执行 |
| `.env` | `spider/.env` 已配置（PGENGINE/PGUSER/PGPWD/PGHOST/PGPORT/PGDB/INDEX 等） |
| 数据库 | PostgreSQL 可连通 |
| 运行时间 | 默认 **周一到周五 16:30**（A 股 15:00 收盘后留 30 分钟余量） |

### 定位 Poetry 安装位置（关键）

部署前必须确认 poetry 的绝对路径，后续 cron 与 launchd 的 PATH 配置都依赖它：

```bash
which poetry
# 示例输出：/Library/Frameworks/Python.framework/Versions/3.11/bin/poetry
```

> ⚠️ macOS launchd 和 Linux cron 给的 PATH 极其精简（通常只有 `/usr/bin:/bin`），**不会**加载 `.zshrc/.bash_profile`，因此 poetry 所在目录必须在脚本/crontab 中显式声明。

---

## 二、统一入口脚本 `scripts/run.sh`

所有定时任务（无论 launchd 还是 cron）都调用同一个入口脚本，它负责：

1. 用 `BASH_SOURCE` 解析项目绝对路径（不依赖 `pwd`）
2. 显式 `export PATH` + 自动探测 poetry 安装位置
3. 日志目录由环境变量 `SPIDER_LOG_DIR` 决定（默认 `$HOME/Library/Logs/spider`）
4. Poetry 缺失直接报错退出（不在定时任务里联网安装）
5. 虚拟环境缺失自动 `poetry install --no-root`
6. `exec poetry run python spider/run.py`

关键片段（poetry 自动探测）：

```bash
POETRY_BIN=""
if command -v poetry >/dev/null 2>&1; then
    POETRY_BIN="$(command -v poetry)"
else
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
            export PATH="$(dirname "$cand"):${PATH}"
            break
        fi
    done
fi
```

---

## 三、macOS 部署：launchd（推荐）

> 相比 cron 的优势：唤醒后会补跑「错过的」任务；不需要折腾 Full Disk Access。

### 3.1 配置文件

`scripts/com.plugin.spider.plist` 关键配置：

| Key | 值 | 说明 |
|-----|----|----|
| Label | `com.plugin.spider` | 全局唯一标识 |
| ProgramArguments | `/bin/bash` + `run.sh` 绝对路径 | 调用入口脚本 |
| WorkingDirectory | `spider/` 绝对路径 | 确保 `.env`/相对路径正确 |
| StartCalendarInterval | Hour=16, Minute=30, Weekday=[1-5] | 周一到周五 16:30 |
| StandardOutPath | `~/Library/Logs/spider/spider.out.log` | 标准输出 |
| StandardErrorPath | `~/Library/Logs/spider/spider.error.log` | 标准错误 |
| KeepAlive | false | 失败不自动重启 |
| RunAtLoad | false | 加载时不立即触发 |

### 3.2 部署步骤

```bash
# 1. 拷贝 plist 到 LaunchAgents 目录
mkdir -p ~/Library/LaunchAgents
cp scripts/com.plugin.spider.plist ~/Library/LaunchAgents/

# 2. 修改 plist 中的绝对路径（如果不是默认 /Users/hengxinliu/startup/Plugin）
#    用编辑器替换用户名和项目路径

# 3. 校验语法
plutil -lint ~/Library/LaunchAgents/com.plugin.spider.plist

# 4. 加载（首次或修改后）
launchctl unload ~/Library/LaunchAgents/com.plugin.spider.plist 2>/dev/null  # 避免重复
launchctl load ~/Library/LaunchAgents/com.plugin.spider.plist

# 5. 确认加载成功
launchctl list | grep plugin
# 期望输出：-  0  com.plugin.spider（第二列 PID，第三列退出码）
```

### 3.3 手动测试

```bash
# 立即触发一次（不等 16:30）
launchctl start com.plugin.spider

# 实时观察日志
tail -f ~/Library/Logs/spider/spider.out.log ~/Library/Logs/spider/spider.error.log
```

### 3.4 卸载

```bash
launchctl unload ~/Library/LaunchAgents/com.plugin.spider.plist
rm ~/Library/LaunchAgents/com.plugin.spider.plist
```

---

## 四、Linux 部署：cron

### 4.1 配置文件

`scripts/spider.cron` 关键内容：

```cron
SHELL=/bin/bash
# PATH 必须包含 poetry 所在目录
PATH=/Library/Frameworks/Python.framework/Versions/3.11/bin:$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin
SPIDER_LOG_DIR=/var/log/spider

30 16 * * 1-5  /bin/bash /opt/Plugin/spider/scripts/run.sh >> /var/log/spider/cron.log 2>&1
```

> ⚠️ 上面 PATH 是 macOS 风格示例；Linux 上 poetry 通常在 `/usr/local/bin` 或 `$HOME/.local/bin`，按实际情况调整。

### 4.2 部署步骤

```bash
# 方式 A：替换现有 crontab（会覆盖！）
crontab scripts/spider.cron

# 方式 B：追加（推荐）
(crontab -l 2>/dev/null; cat scripts/spider.cron | grep -v '^#') | crontab -

# 确认
crontab -l
```

### 4.3 排错命令

```bash
# Debian/Ubuntu
grep CRON /var/log/syslog

# RHEL/CentOS
tail -f /var/log/cron

# 爬虫运行日志
tail -f /var/log/spider/spider.{out,error}.log
```

---

## 五、实际验证记录（2026-08-02）

本次在 macOS 上真实部署并验证，过程如下。

### 5.1 部署与触发

```bash
mkdir -p ~/Library/LaunchAgents
cp spider/scripts/com.plugin.spider.plist ~/Library/LaunchAgents/
launchctl unload ~/Library/LaunchAgents/com.plugin.spider.plist 2>/dev/null
launchctl load ~/Library/LaunchAgents/com.plugin.spider.plist
launchctl start com.plugin.spider      # 手动触发
```

### 5.2 首次触发失败（退出码 127）

**现象**：`launchctl list` 显示 `127`，`~/Library/Logs/spider/spider.error.log` 出现：
```
[FATAL] 2026-08-02 17:51:49 Poetry 未安装，PATH=/Users/hengxinliu/.local/bin:...:/usr/bin:/bin
```

**根因**：launchd 的 PATH 只有 `/usr/bin:/bin` 等，poetry 实际在 `/Library/Frameworks/Python.framework/Versions/3.11/bin/`，不在预设 PATH 中。

**修复**：在 `run.sh` 增加 poetry 自动探测逻辑（见第二节），覆盖 macOS Python.framework / Homebrew / pyenv / Linux 常见安装位置。

### 5.3 二次触发成功

```bash
launchctl start com.plugin.spider
```

进程 PID 41942 起来，`~/Library/Logs/spider/spider.out.log` 出现：
```
[INFO] 2026-08-02 17:52:21 Starting spider in Poetry environment, dir=/Users/hengxinliu/startup/Plugin/spider
```

### 5.4 四个爬虫执行结果

| 爬虫 | 启动 | 结束 | 日志 | 产出 |
|------|------|------|------|------|
| Stock | 17:52:25 | 17:52:41 | stock_20260802_175225.log | feeds/stock_20260802_175225.jsonl (190B) |
| Adjustment | 17:52:41 | 17:54:03 | adj_20260802_175225.log | feeds/adjustment_20260802_175241.jsonl (4.4KB) |
| Rightment | 17:54:03 | 17:54:xx | rgt_20260802_175225.log | feeds/rightment_20260802_175403.jsonl (0B，无新数据) |
| Benchmark | 17:54:xx | 17:54:xx | benchmark_20260802_175225.log | 4 个 parquet（Q3/202607）|

每个爬虫日志末尾均为：
```
2026-08-02 17:5x:xx [scrapy] INFO: Spider closed (finished)
```

### 5.5 最终状态

```bash
$ launchctl list | grep plugin
-  0  com.plugin.spider
```

退出码 `0` = 上次执行成功，正在待命等待下一个交易日 16:30。

---

## 六、常见排错速查

| 现象 | 原因 | 解决 |
|------|------|------|
| 退出码 127 | PATH 找不到 poetry | 确认 `which poetry`，更新 run.sh 探测列表或 crontab PATH |
| 退出码 1 | Python 报错 | 查看 `~/Library/Logs/spider/spider.error.log` 或 spider/logs/*.log |
| 任务不触发 | plist 语法错误或路径错 | `plutil -lint`；确认 plist 内绝对路径 |
| `.env` 不生效 | WorkingDirectory 不对 | 确认 plist 的 `WorkingDirectory` 指向 `spider/` |
| 节假日空跑 | cron/launchd 不识别交易日 | 依赖爬虫增量过滤；如需精确可在 run.sh 开头加交易日历判断 |
| 数据库连不上 | `.env` 缺失或网络问题 | 检查 PGPWD/PGHOST；手动 `poetry run python spider/run.py` 验证 |

---

## 七、修改运行时间

### launchd
编辑 `~/Library/LaunchAgents/com.plugin.spider.plist` 的 `<key>StartCalendarInterval</key>` 段，然后：
```bash
launchctl unload ~/Library/LaunchAgents/com.plugin.spider.plist
launchctl load ~/Library/LaunchAgents/com.plugin.spider.plist
```

### cron
编辑 `scripts/spider.cron` 最后一行 5 个字段（分 时 日 月 周），然后：
```bash
crontab scripts/spider.cron   # 或 crontab -e 手动改
```

---

## 八、文件清单

| 文件 | 用途 |
|------|------|
| `scripts/run.sh` | 统一入口（poetry 自动探测、日志路径、虚拟环境检查）|
| `scripts/com.plugin.spider.plist` | macOS LaunchAgent 模板 |
| `scripts/spider.cron` | Linux crontab 片段 |
| `scripts/DEPLOYMENT.md` | 本文档 |