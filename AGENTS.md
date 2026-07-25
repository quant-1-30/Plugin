# AGENTS.md — Plugin 项目指南
---

## 1. 项目概述

**Plugin** 是一个围绕 Scrapy 构建的 A 股金融数据采集套件，目前核心代码位于 `spider/` 子目录。

主要采集目标：

| 爬虫 | 名称 | 说明 | 落地方式 |
|------|------|------|----------|
| `Stock` | `stock` | A 股基础证券列表（代码、名称、首发交易日） | PostgreSQL + `feeds/jsonl` |
| `Adjustment` | `adjustment` | 分红送转/除权除息数据（报告日、登记日、除权除息日、送股、转股、派息） | PostgreSQL + `feeds/jsonl` |
| `Rightment` | `rightment` | 配股数据（报告日、登记日、除权日、配股比例、配股价格） | PostgreSQL + `feeds/jsonl` |
| `Benchmark` | `benchmark` | 大盘/指数分钟级 tick 数据（开高低收成交量成交额） | Hive 分区 Parquet（`data/benchmark`） |

数据来源以东方财富（`push2.eastmoney.com`、`push2his.eastmoney.com`、`push2delay.eastmoney.com`）和新浪财经（`finance.sina.com.cn`）为主。

---

## 2. 目录结构

```
Plugin/
├── Readme.md                 # 项目级随手笔记（偏运维/数据库片段）
├── AGENTS.md                 # 本文件
├── .gitignore                # 标准 Python gitignore，并忽略 logs/feeds/data 产出
├── contrib/                  # 参考/备用代码，未接入主流程
│   ├── pipeline.py           # 基于 h5py 的 OHLCV HDF5 写入器（zipline 风格）
│   └── xpath.py              # 使用 XPath + Sina 页面的旧版分红/配股/股本结构爬虫
└── spider/                   # 主项目（Scrapy project）
    ├── Readme.md             # Scrapy 知识点笔记（中文为主）
    ├── pyproject.toml        # Poetry 依赖配置
    ├── poetry.lock           # Poetry 锁定文件
    ├── scrapy.cfg            # Scrapy 项目配置
    ├── .env                  # 数据库/URL 等敏感配置（已 gitignore）
    ├── scripts/
    │   └── run.sh            # 生产/定时启动入口脚本
    ├── data/                 # benchmark 输出的 Hive 分区 Parquet
    ├── feeds/                # JSONL feed 输出
    ├── logs/                 # 各爬虫日志文件
    ├── tests/                # 测试目录（当前为空）
    └── spider/               # 核心代码包
        ├── settings.py       # Scrapy 全局设置
        ├── run.py            # 程序入口：顺序启动 4 个爬虫
        ├── constant.py       # benchmark 指数代码映射
        ├── encoder.py        # JSONEncoder（bytes/np 类型/日期）
        ├── export.py         # 预留的 feed exporter（当前未启用）
        ├── crawlers/         # 爬虫实现
        ├── pipelines/        # Item 与 Pipeline 实现
        ├── middlewares/      # 下载器/爬虫中间件
        ├── extensions/       # Scrapy 扩展（统计、邮件）
        └── utils/            # 数据库、工具函数
```

---

## 3. 技术栈

- **Python**：`>=3.11,<3.13`
- **依赖管理**：Poetry（`pyproject.toml` + `poetry.lock`）
- **爬虫框架**：Scrapy `2.13`
- **异步运行时**：Twisted + `AsyncioSelectorReactor`（`settings.py` 与 `run.py` 均显式安装）
- **数据库**：PostgreSQL，驱动使用 `asyncpg`，通过 SQLAlchemy `2.0` 异步会话操作
- **数据处理**：`pandas`、`numpy`、`pyarrow`、`h5py`、`toolz`
- **其他**：`lxml`、`parsel`、`httpx`、`dotenv`
- **包索引**：清华 TUNA 镜像（`pyproject.toml` 中配置为 `priority = "default"`）

---

## 4. 构建与运行命令

所有操作默认在 `spider/` 目录下进行。

### 4.1 安装依赖

```bash
cd spider
poetry install --no-root
```

如果本地没有 Poetry，`scripts/run.sh` 会自动通过官方脚本安装。

### 4.2 运行全部爬虫（推荐入口）

```bash
cd spider
poetry run python spider/run.py
```

`run.py` 会按 **Stock → Adjustment → Rightment → Benchmark** 的顺序串行执行，每个爬虫都是一个 Twisted `Deferred`，通过 `CrawlerRunner` 调度。

### 4.3 通过启动脚本运行

```bash
cd spider
bash scripts/run.sh
```

该脚本会：

1. 把当前目录加入 `PYTHONPATH`。
2. 确保 `/var/log/spider.error.log` 与 `/var/log/spider.out.log` 存在并设置权限。
3. 检查 Poetry 是否安装，必要时自动安装。
4. 检查虚拟环境是否存在，否则执行 `poetry install --no-root`。
5. 执行 `poetry run python spider/run.py`。

脚本注释中还留有 `supervisorctl`、`launchctl plist` 与 `nohup` 的运维提示，但仓库中未提供具体配置文件。

### 4.4 单独运行某个爬虫（Scrapy CLI）

```bash
cd spider
poetry run scrapy crawl stock
poetry run scrapy crawl adjustment
poetry run scrapy crawl rightment
poetry run scrapy crawl benchmark
```

---

## 5. 代码组织与模块划分

### 5.1 爬虫（`spider/crawlers/`）

- `base.py`：`BaseSpider`
  - 统一 `allowed_domains`。
  - 提供 `_extract_json_with_retry()`：自动处理 gzip，JSON 解析失败时返回重试请求。
  - 提供 `errback_httpbin()`：记录下载异常。
- `asset.py`：`Stock` —— 全量 A 股列表。
- `adj.py`：`Adjustment` —— 分红送转，按季度日期增量抓取。
- `rgt.py`：`Rightment` —— 配股数据。
- `benchmark.py`：`Benchmark` —— 指数分钟 tick。
- `__init__.py`：导出四个爬虫类，供 `run.py` 批量导入。

每个活跃爬虫都：

- 在 `custom_settings` 中启用 `UserAgentMiddleware` 与 `CustomRetryMiddleware`。
- 通过 `ITEM_PIPELINES` 挂载对应的业务 Pipeline + `AsyncDb` + `JsonlFeed`（benchmark 使用 `ParquetWriter`）。
-  asset/adj/rgt 在 `spider_opened` 信号中通过 `async_ops.on_query()` 查询数据库获取最新日期，用于增量过滤。

### 5.2 Item 与 Pipeline（`spider/pipelines/`）

- `items.py`：定义 `AssetItem`、`TickItem`、`Dividend`、`Right`。
- `pipelines.py`：
  - `Asset` / `Adjustment` / `Rightment`：清洗字段、过滤已存在数据、统一日期格式。
  - `AsyncDb`：后台 asyncio 消费者，将 item 批量写入 PostgreSQL（默认 `batch_size=1`，通过 `POSTGRES_BATCH_SIZE` 设置）。
  - `JsonlFeed`：把 item 写入 `feeds/jsonl/{name}_{timestamp}.jsonl`。
  - `ParquetWriter`：将 benchmark tick 按 `year/quarter/sid/date` Hive 分区写入 `data/benchmark`。

### 5.3 中间件（`spider/middlewares/`）

- `download.py`：
  - `UserAgentMiddleware`：从 `USER_AGENT` 列表随机选择 UA。
  - `CustomRetryMiddleware`：自定义重试逻辑。
  - `HttpProxyMiddleware`：代理支持（当前未在活跃爬虫中启用）。
  - `RedirectMiddleware`：处理 301/302。
- `spider.py`：
  - `ErrorSpiderMiddleware`：拦截错误状态码。
  - `HttpErrorMiddleware`：非 200 响应过滤。

### 5.4 扩展（`spider/extensions/`）

- `CoreStats`：记录启动/结束时间、item 数、响应数、drop 原因统计。
- `StatsMailer`：爬虫关闭后通过 163 SMTP 发送统计邮件（依赖 `settings.py` 中的 `MAIL_*` 配置）。

### 5.5 工具（`spider/utils/`）

- `operator.py`：`AsyncOps` 单例，封装 SQLAlchemy 异步引擎与会话，提供 `on_query`、`on_insert`、`on_execute`。
- `tools.py`：季度日期生成、相邻季度计算、重试请求构造、`coerce_to_uint32`。

### 5.6 配置常量

- `spider/constant.py`：`index_mapping`，将指数代码（如 `000001`）映射为输出 sid（如 `1A0001`）。

---

## 6. 配置与环境变量

### 6.1 Scrapy 配置（`spider/settings.py`）

- `BOT_NAME = 'backtest'`
- `SPIDER_MODULES = ['spider.crawlers']`
- `TWISTED_REACTOR = 'twisted.internet.asyncioreactor.AsyncioSelectorReactor'`
- 默认关闭 `ROBOTSTXT_OBEY`、`COOKIES_ENABLED`、`TELNETCONSOLE_ENABLED`、`REDIRECT_ENABLED`。
- 启用 `AUTOTHROTTLE`、`RETRY`、自定义下载延迟与并发控制。
- 默认 `ITEM_PIPELINES` 为空，实际 pipeline 由各爬虫 `custom_settings` 覆盖。

### 6.2 环境变量（`spider/.env`）

`.env` 文件由 `run.py` 通过 `dotenv.load_dotenv()` 加载，包含数据库连接、目标 URL、指数列表等敏感信息。由于该文件被 `.gitignore` 忽略，新环境需要手动创建。代码中读取到的关键变量包括：

- `PGENGINE`、`PGUSER`、`PGPWD`、`PGHOST`、`PGPORT`、`PGDB`、`PGPOOLSIZE`、`PGTIMEOUT`、`PGMAXOVERFLOW`、`PGPOOLRECYCLE`、`PGPREPING`、`PGECHO`
- `ASSET_URL`、`ADJ_URL`、`RGT_URL`、`INDEX_URL`
- `INDEX`

> 请勿在代码中硬编码数据库密码或邮件密码；当前 `settings.py` 中仍保留有代理账号与邮件授权码等明文，应逐步迁移至 `.env` 或密钥管理工具。

---

## 7. 运行时架构

1. `run.py` 安装 `AsyncioSelectorReactor` 并调用 `load_dotenv()`。
2. 使用 `CrawlerRunner(get_project_settings())` 创建 runner。
3. `crawl()` 函数通过 `defer.inlineCallbacks` 串行调度四个爬虫。
4. 每个爬虫在 `spider_opened` 中异步查询 PostgreSQL 获取最新数据点，用于增量过滤。
5. `start_requests` 生成初始请求，`parse` 为 `async def`，解析 JSON 后产出 Item。
6. Item 经过业务 Pipeline 清洗，再进入：
   - `AsyncDb`：写入 PostgreSQL。
   - `JsonlFeed`：写入本地 JSONL。
   - benchmark 额外进入 `ParquetWriter`，生成按 `year/quarter/sid/date` 分区的 Parquet。
7. 爬虫结束时，`AsyncDb` 关闭后台消费者并 flush 剩余数据；`ParquetWriter` 将 buffer 写入 Parquet。
8. `CoreStats` / `StatsMailer` 在关闭时汇总并邮件发送统计信息。

---

## 8. 开发规范

- **文件头**：Python 文件使用 `#!/usr/bin/env python3` + `# -*- coding: utf-8 -*-` 头，并带有统一创建时间注释块。
- **编码**：全项目使用 UTF-8，中文注释常见。
- **字符串**：f-string 与 `%` 格式化混用，保持与周围代码风格一致即可。
- **异步**：爬虫回调使用 `async def parse(...)`；数据库操作通过 `asyncio.run_coroutine_threadsafe` + `defer.Deferred.fromFuture` 桥接到 Twisted。
- **日志**：各爬虫在 `custom_settings` 中配置独立 `LOG_FILE`，统一格式为 `%(asctime)s [%(name)s] %(levelname)s: %(message)s`。
- **新增爬虫**：继承 `BaseSpider`，定义 `name`、`table_name`、`custom_settings`，并在 `spider/__init__.py` 与 `run.py` 中注册。
- **新增 Pipeline**：继承 `Pipeline` 基类，实现 `process_item`，必要时实现 `open_spider` / `close_spider`，并在对应爬虫 `custom_settings.ITEM_PIPELINES` 中按优先级挂载。

---

## 9. 测试说明

- 项目存在 `spider/tests/` 目录，但当前为空。
- 没有配置 `pytest`、`tox` 或 CI 流水线。
- 建议后续补充：
  - 各爬虫 `parse` 回调的单元测试（使用 `scrapy.http.TextResponse` 固定样本）。
  - Pipeline 清洗逻辑测试。
  - `AsyncDb` 的 mock 测试。

---

## 10. 部署与运维

- 当前主要部署方式是直接运行 `spider/scripts/run.sh`。
- 脚本注释中提及 `supervisorctl` 与 macOS `launchctl plist`，但未提供具体配置文件。
- benchmark 输出存放在 `spider/data/benchmark`，按 Hive 风格分区：`year=YYYY/quarter=Q{1-4}/sid=<sid>/date=YYYYMM/`。
- JSONL feed 输出存放在 `spider/feeds/jsonl/`。
- 日志输出存放在 `spider/logs/`。

---

## 11. 安全注意事项

- **敏感信息硬编码**：`spider/settings.py` 中直接写入了代理 IP 列表（含用户名密码）以及邮件 SMTP 授权码。这些属于敏感凭证，应尽快迁移到 `.env` 文件或专用密钥管理服务，并通过 `crawler.settings.get(...)` 读取。
- **`.env` 文件**：已加入 `.gitignore`，不会进入版本控制。在新增环境或 CI 中需要手动注入对应变量。
- **数据库连接**：`spider/utils/operator.py` 通过环境变量拼接 PostgreSQL URL，请确保 `.env` 中的 `PGPWD` 强度足够且网络访问受限。
- **Robots 与法律合规**：项目设置 `ROBOTSTXT_OBEY = False`，且采集的是第三方金融数据。修改或扩展爬虫时请遵守目标网站的 `robots.txt`、服务条款及当地数据合规要求。
- **代理中间件**：`HttpProxyMiddleware` 已实现但当前未在活跃爬虫中启用；启用前请确认代理来源合法、可用且已轮换。

---

## 12. 常见问题速查

- **Reactor 相关报错**：`run.py` 已经在任何 Twisted 导入前调用 `asyncioreactor.install()`，不要再次安装或手动创建事件循环。
- **数据库写入没有反应**：检查 `.env` 是否正确加载，`AsyncDb` 默认 `batch_size=1`，可以调大 `POSTGRES_BATCH_SIZE` 提升吞吐。
- **增量过滤失效**：asset/adj/rgt 依赖 `spider_opened` 中查询数据库的最新日期，请确认 PostgreSQL 中对应表有数据且字段名正确。
- **benchmark 输出为空**：`Benchmark` 只写入 `data/benchmark`，不写入数据库或 JSONL；检查 `INDEX` 环境变量是否配置正确。
