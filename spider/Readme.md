# Plugin · Spider

> 基于 Scrapy 的 A 股金融数据采集套件。采集证券基础信息、分红送转、配股、指数分钟级 tick，分别落地到 PostgreSQL、JSONL、Hive 分区 Parquet。

---

## 目录

- [一、采集能力总览](#一采集能力总览)
- [二、目录结构](#二目录结构)
- [三、快速开始](#三快速开始)
- [四、架构与数据流](#四架构与数据流)
- [五、爬虫详解](#五爬虫详解)
- [六、Pipeline 体系](#六pipeline-体系)
- [七、中间件](#七中间件)
- [八、扩展](#八扩展)
- [九、数据库与分区](#九数据库与分区)
- [十、定时部署](#十定时部署)
- [十一、优化点与改进方向](#十一优化点与改进方向)
- [附录：A 股业务术语速查](#附录a-股业务术语速查)

---

## 一、采集能力总览

| 爬虫类 | name | 数据源 | 采集内容 | 落地目标 |
|--------|------|--------|----------|----------|
| `Stock` | `stock` | 东方财富 `push2.eastmoney.com` | A 股证券列表（代码、名称、首发交易日） | PostgreSQL `asset` + JSONL |
| `Adjustment` | `adjustment` | 东方财富 `datacenter-web.eastmoney.com` | 分红送转（报告日、登记日、除权除息日、送股、转股、派息） | PostgreSQL `adjustment` + JSONL |
| `Rightment` | `rightment` | 东方财富 `datacenter-web.eastmoney.com` | 配股（报告日、登记日、除权日、配股比例、配股价格） | PostgreSQL `rightment` + JSONL |
| `Benchmark` | `benchmark` | 东方财富 `push2his.eastmoney.com` | 指数分钟级 tick（开高低收、成交量、成交额） | Hive 分区 Parquet `data/benchmark` |

四个爬虫在 `run.py` 中按 **Stock → Adjustment → Rightment → Benchmark** 顺序串行执行。

---

## 二、目录结构

```
spider/
├── pyproject.toml          # Poetry 依赖
├── scrapy.cfg
├── .env                    # 数据库/URL/指数配置（gitignore）
├── scripts/
│   ├── run.sh              # 统一启动入口（适配手动/cron/launchd）
│   ├── com.plugin.spider.plist  # macOS LaunchAgent 模板
│   ├── spider.cron         # Linux crontab 片段
│   └── DEPLOYMENT.md       # 定时部署完整文档
├── data/benchmark/         # Parquet 输出（Hive 分区）
├── feeds/jsonl/            # JSONL feed 输出
├── logs/                   # 各爬虫独立日志
├── tests/                  # 测试（当前为空）
└── spider/                 # 核心代码包
    ├── run.py              # 程序入口：CrawlerRunner 串行调度 4 个爬虫
    ├── settings.py         # Scrapy 全局设置
    ├── constant.py         # 指数代码映射 index_mapping
    ├── encoder.py          # CustomFeedJsonEncoder（bytes/np/日期）
    ├── crawlers/           # 爬虫实现
    │   ├── base.py         # BaseSpider（gzip 解压 + JSON 重试 + errback）
    │   ├── asset.py        # Stock
    │   ├── adj.py          # Adjustment
    │   ├── rgt.py          # Rightment
    │   └── benchmark.py    # Benchmark
    ├── pipelines/
    │   ├── items.py        # AssetItem / Dividend / Right / TickItem
    │   └── pipelines.py    # 业务清洗 + AsyncDb + JsonlFeed + ParquetWriter
    ├── middlewares/
    │   ├── download.py     # UA / Proxy / Retry / Redirect
    │   └── spider.py       # ErrorSpiderMiddleware / HttpError
    ├── extensions/
    │   └── stats.py        # CoreStats + StatsMailer
    └── utils/
        ├── operator.py     # AsyncOps：SQLAlchemy 异步引擎 + Deferred 桥接
        └── tools.py        # quarter_date / get_adjacent_quarter / get_retry_request
```

---

## 三、快速开始

### 环境要求

- Python `>=3.11, <3.13`
- Poetry
- PostgreSQL（asset / adjustment / rightment 表需预先建好）

### `.env` 必填项

在 `spider/.env` 中配置（已被 gitignore）：

```dotenv
# 数据库
PGENGINE=asyncpg
PGUSER=...
PGPWD=...
PGHOST=...
PGPORT=5432
PGDB=...
PGPOOLSIZE=20
PGTIMEOUT=30
PGMAXOVERFLOW=10
PGPOOLRECYCLE=3600
PGPREPING=1
PGECHO=0

# 采集 URL
ASSET_URL=https://push2.eastmoney.com/api/qt/clist/get?
ADJ_URL=https://datacenter-web.eastmoney.com/api/data/v1/get?
RGT_URL=https://datacenter-web.eastmoney.com/api/data/v1/get?
INDEX_URL=https://push2his.eastmoney.com/api/qt/stock/trends2/get?

# benchmark 指数列表（逗号分隔，格式 secid）
INDEX=1.000001,1.000688,0.399001,0.399006
```

### 安装与运行

```bash
cd spider
poetry install --no-root

# 单独运行某个爬虫
poetry run scrapy crawl stock
poetry run scrapy crawl adjustment
poetry run scrapy crawl rightment
poetry run scrapy crawl benchmark

# 串行运行全部（推荐）
poetry run python spider/run.py

# 通过启动脚本（适配定时任务）
bash scripts/run.sh
```

---

## 四、架构与数据流

```
run.py (CrawlerRunner, 串行 Deferred 链)
  │
  ├─ Stock ──────────┐
  ├─ Adjustment ─────┤  每个爬虫内部：
  ├─ Rightment ──────┤   1) spider_opened 信号 → async_ops.on_query() 查增量水位
  └─ Benchmark ──────┘   2) start_requests → 东方财富 API
                         3) async def parse → _extract_json_with_retry → ItemLoader → Item
                         4) Pipeline 链：
                            业务清洗(Asset/Adjustment/Rightment)
                              → AsyncDb(asyncio Queue → SQLAlchemy → PG)
                              → JsonlFeed(本地 JSONL)
                              或
                              → ParquetWriter(Hive 分区 Parquet)
```

**异步桥接关键**：Scrapy 运行在 Twisted `AsyncioSelectorReactor` 上。数据库操作通过 `asyncio.run_coroutine_threadsafe(coro, reactor._asyncioEventloop)` 提交到 reactor 内嵌的 asyncio loop，再用 `Deferred.fromFuture()` 转回 Twisted 语义，避免阻塞主线程。

---

## 五、爬虫详解

### 公共基类 `BaseSpider`（`crawlers/base.py`）

- 统一 `allowed_domains`（东方财富三个域名）
- `_extract_json_with_retry(response)`：自动 gzip 解压 + JSON 解析；失败时通过 `get_retry_request` 返回重试请求
- `errback_httpbin(failure)`：记录下载异常（Timeout/DNS/Connection 等）

### 5.1 Stock（`asset.py`）

| 项 | 说明 |
|----|------|
| 增量水位 | `SELECT max(first_trading) FROM asset` |
| 数据源参数 | `fs=m:0+f:8,m:1+f:8`（沪市正常 + 深市正常），`fid=f26` 按 IPO 日期排序 |
| 字段映射 | `f12→sid`, `f14→name`, `f26→first_trading` |
| 分页 | `pn` 递增直到无 diff |
| 清洗规则 | `first_trading > max_date` 才入库；sid/name 编码为 bytes |

### 5.2 Adjustment（`adj.py`）

| 项 | 说明 |
|----|------|
| 增量水位 | 窗口函数取每个 sid 的最新 `ex_date` |
| 起始日期 | `get_adjacent_quarter` 取水位后退一年，再枚举季度 |
| 数据源 | `reportName=RPT_SHAREBONUS_DET`，按 `REPORT_DATE` 过滤 |
| 字段映射 | `SECUCODE→sid`, `REPORT_DATE→report_date`, `EQUITY_RECORD_DATE→register_date`, `EX_DIVIDEND_DATE→ex_date`, `BONUS_RATIO→bonus_share`, `IT_RATIO→transfer`, `PRETAX_BONUS_RMB→bonus` |
| 分页 | `pageNumber` 递增直到 `pages` |
| 清洗规则 | 仅匹配 `^[630]\d{5}` 的 sid（主板/创业板），日期转 `YYYYMMDD` int |

### 5.3 Rightment（`rgt.py`）

| 项 | 说明 |
|----|------|
| 增量水位 | 同 Adjustment，取每个 sid 最新 `ex_date` |
| 数据源 | `reportName=RPT_IPO_ALLOTMENT`，按 `EQUITY_RECORD_DATE` 排序 |
| 字段映射 | `SECUCODE→sid`, `FIRST_NOTICE_DATE→report_date`, `EQUITY_RECORD_DATE→register_date`, `EX_DIVIDEND_DATE→ex_date`, `PLACING_RATIO→ratio`, `ISSUE_PRICE→price` |
| 清洗规则 | 日期转 `YYYYMMDD` int；`ex_date > 水位` 才入库 |

### 5.4 Benchmark（`benchmark.py`）

| 项 | 说明 |
|----|------|
| 数据源 | `push2his.eastmoney.com` 的 `trends2` 接口，`ndays=1`（当日分钟线） |
| 指数列表 | 来自 `.env` 的 `INDEX`（如 `1.000001`） |
| 字段映射 | `code→sid`，`trends` 字符串 split → tick/open/close/high/low/volume/amount |
| 落地 | 不入库，直接进 `ParquetWriter` 写 Hive 分区 Parquet |
| sid 映射 | `constant.index_mapping`（`000001→1A0001` 等） |

---

## 六、Pipeline 体系

### 6.1 基类 `Pipeline`（`pipelines.py`）

提供 `from_crawler` 自动绑定 `open_spider/close_spider` 信号与 `logger`。

### 6.2 业务清洗 Pipeline

| Pipeline | 作用 |
|----------|------|
| `Asset` | `valmap` 展平 ItemLoader 列表值；`first_trading > max` 过滤；sid/name 编码 bytes |
| `Adjustment` | 正则过滤主板/创业板 sid；日期 `YYYY-MM-DD HH:MM:SS → int(YYYYMMDD)`；`ex_date > 水位` 去重 |
| `Rightment` | 同 Adjustment 的日期处理；`ex_date > 水位` 去重 |

### 6.3 `AsyncDb`（异步批量写库）

- `open_spider`：创建 `asyncio.Queue`，启动后台 `_consume_loop` 消费者
- `process_item`：`put_nowait` 入队（非阻塞），item 继续向后传
- `_consume_loop`：按 `batch_size`（默认 **1**，由 `POSTGRES_BATCH_SIZE` 控制）攒批 → `force_flush` → SQLAlchemy ` executemany`
- `close_spider`：发送 `_stop_signal` → join worker → 最后一次 `force_flush`，返回 `Deferred` 确保关闭前写完

### 6.4 `JsonlFeed`

每个 item 写一行 JSON（`indent=4`，`CustomFeedJsonEncoder` 处理 bytes/numpy/date）。文件名 `feeds/jsonl/{name}_{timestamp}.jsonl`。

### 6.5 `ParquetWriter`（Benchmark 专用）

- `process_item`：buffer 累积 dict
- `close_spider`：`pd.DataFrame` → `_prepare_dataframe`（时区 `Asia/Shanghai`、tick 转 UTC int64、生成分区列 year/quarter/date、sid 经 `index_mapping` 映射）
- `pyarrow.dataset.write_dataset` 写 Hive 分区：`year=YYYY/quarter=Qx/sid=XXX/date=YYYYMM/`，`existing_data_behavior=overwrite_or_ignore`

---

## 七、中间件

### 下载器中间件（`middlewares/download.py`）

| 中间件 | 作用 | 启用状态 |
|--------|------|----------|
| `UserAgentMiddleware` | 从 `USER_AGENT` 列表随机选 UA | ✅ 所有爬虫启用 |
| `CustomRetryMiddleware` | 自定义重试，复用 `get_retry_request`，指数退避 `2**retry_times` | ✅ 所有爬虫启用 |
| `HttpProxyMiddleware` | 随机选 `USER_PROXY_IP` 代理，支持 `user:pass@host` Basic 认证 | ⚠️ 已实现但被注释 |
| `RedirectMiddleware` | 处理 301/302 | 项目默认 `REDIRECT_ENABLED=False` |
| `HttpAuthMiddleware` | Basic HTTP 认证 | 备用 |

### 爬虫中间件（`middlewares/spider.py`）

- `ErrorSpiderMiddleware`：错误状态码拦截
- `HttpErrorMiddleware`：非 200 过滤

---

## 八、扩展（`extensions/stats.py`）

| 扩展 | 作用 |
|------|------|
| `CoreStats` | 记录 start/finish/elapsed、item_scraped/dropped、response_received |
| `StatsMailer` | 爬虫关闭后通过 163 SMTP 发送统计邮件（依赖 `MAIL_*` 配置） |

---

## 九、数据库与分区

### PostgreSQL 表

| 表 | 关键字段 | 去重约束 |
|----|----------|----------|
| `asset` | sid(bytes), name(bytes), first_trading(int) | `max(first_trading)` 增量 |
| `adjustment` | sid, report_date, register_date, ex_date, bonus_share, transfer, bonus | `(sid, ex_date)` 业务去重 |
| `rightment` | sid, report_date, register_date, ex_date, ratio, price | `(sid, report_date)` 唯一约束 |

### Benchmark Parquet 分区

```
data/benchmark/
└── year=2026/
    └── quarter=Q3/
        └── sid=1A0001/
            └── date=202607/
                └── daily_benchmark_20260802_175451_0.parquet
```

schema 中 `datetime` 为 `timestamp[ms, tz=UTC]`，分区列为 string。

---

## 十、定时部署

完整部署文档见 **[scripts/DEPLOYMENT.md](scripts/DEPLOYMENT.md)**（含 macOS launchd 与 Linux cron 的实际验证记录）。

要点：
- 统一入口：`scripts/run.sh`（自动探测 poetry 路径、`SPIDER_LOG_DIR` 可配置）
- 默认调度：周一到周五 16:30（A 股 15:00 收盘后 30 分钟）
- macOS：`launchctl load ~/Library/LaunchAgents/com.plugin.spider.plist`
- Linux：`crontab scripts/spider.cron`

---

## 十一、优化点与改进方向

以下是代码审查中发现的**真实可优化项**，按优先级排序。

### 🔴 高优先级（安全/正确性）

| # | 问题 | 位置 | 建议 |
|---|------|------|------|
| 1 | **硬编码敏感凭证** | `settings.py` `USER_PROXY_IP`（含代理账号密码）、`MAIL_PASS`（SMTP 授权码） | 迁移到 `.env`，通过 `crawler.settings.get()` 读取 |
| 2 | **`AsyncDb` 默认 `batch_size=1`** | `pipelines.py` L155 | 逐条写库吞吐极低，建议默认 50-100 |
| 3 | **`AsyncOps.on_query` 吞噬异常** | `operator.py` L134-137 | 异常时返回 `[]`，导致增量水位丢失、全量重抓。应抛出或显式告警 |
| 4 | **`Adjustment` 正则漏板块** | `pipelines.py` L103 `^[630]\d{5}` | 漏掉科创板 `688`、北交所 `8/4`。建议按交易所归属或 `code[:3]` 白名单 |

### 🟡 中优先级（健壮性）

| # | 问题 | 位置 | 建议 |
|---|------|------|------|
| 5 | **`AsyncDb.close` 顺序风险** | `pipelines.py` L221/242 | `force_flush` 与 worker 停止的先后顺序需明确，避免 buffer 残留丢数据 |
| 6 | **`ParquetWriter` 全量覆盖** | `pipelines.py` L355 `overwrite_or_ignore` | 每次重写整个 sid 分区，无增量合并。建议 `merge` 或按日期分区覆盖 |
| 7 | **`get_adjacent_quarter` 跨年边界** | `tools.py` L64 | `year - offset` 回退方式在跨年时可能漏季度，建议直接取季度序列首项 |
| 8 | **节假日空跑** | `scripts/` | 定时任务不识别交易日历，建议 `run.sh` 开头加交易日历判断 |

### 🟢 低优先级（代码质量）

| # | 问题 | 位置 | 建议 |
|---|------|------|------|
| 9 | **`parse` 是伪 async** | `adj/rgt/asset/benchmark` | `async def` 内无 `await`，去掉 async 或真正 await IO |
| 10 | **`print` 调试残留** | `asset.py` L133, `benchmark.py` L92 | 改用 `self.logger.info` |
| 11 | **`HttpProxyMiddleware` 死代码** | 各爬虫 `custom_settings` 中被注释 | 启用或删除 |
| 12 | **`BaseSpider.from_crawler` dead code** | `base.py` L31-37 | 清理注释 |
| 13 | **无测试** | `tests/` 为空 | 补 `parse` 回调与 Pipeline 清洗的单测 |

---

## 附录：A 股业务术语速查

### 科创板/创业板证券简称后缀

| 后缀 | 含义 |
|------|------|
| N | 新股上市首日 |
| C | 上市第 2-5 日（无涨跌幅限制期间） |
| U | 发行人尚未盈利 |
| W | 表决权差异安排（同股不同权） |
| V | 协议控制架构（VIE） |
| D | 以 CDR（中国存托凭证）形式上市 |

> 科创板/创业板有 ST 制度，涨跌幅限制为 20%（即便 ST 后仍为 20%）。

### 分红送转关键字段

| 字段 | 含义 |
|------|------|
| `register_date` | 股权登记日 |
| `ex_date` | 除权除息日 |
| `bonus_share` | 送股（每 10 股） |
| `transfer` | 转增（每 10 股） |
| `bonus` | 派息（税前，元/10 股） |

> 登记日后的下一个交易日为除权日；该日买入的股东不再享有本次分红。
> 上交所红股上市日 = 除权日次日；深交所 = 登记日后第 3 个交易日。

### 配股关键字段

| 字段 | 含义 |
|------|------|
| `ratio` | 配股比例 |
| `price` | 配股价格（元） |