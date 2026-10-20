# !/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Mar 12 15:37:47 2019

@author: python
"""

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html

# useful for handling different item types with a single interface
import os
import json
import asyncio
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.dataset as ds

from pathlib import Path
from toolz import valmap
from scrapy import signals
from twisted.internet.defer import Deferred
from collections import namedtuple
from datetime import datetime
from scrapy.exceptions import DropItem  
from spider.encoder import CustomFeedJsonEncoder

from utils.tools import (
    is_valid_ashare_sid,
    encode_sid,
    parse_datetime_to_int,
    parse_trading_date_int,
)
from utils.operator import async_ops, _get_reactor_loop
from spider.constant import index_mapping


__all__ = ['Asset', 'Adjustment', 'Rightment', 'AsyncDb', 'JsonlFeed', 'ParquetWriter']


namedData = namedtuple('namedData', ['table_name', 'item'])


class Pipeline:
    """
        enroll into mysql according to owner sid item
    """

    @classmethod
    def from_crawler(cls, crawler):
        instance = cls()
        instance.logger = crawler.spider.logger
        return instance

    # core method
    def process_item(self, item, spider):
        # itemloader add_value to return list object
        raise NotImplementedError


class CorporateActionPipeline(Pipeline):
    """分红送转与配股公共清洗基类，负责日期格式化、A股代码校验、数据库水位对比及当次运行去重。"""

    def __init__(self):
        self.seen_keys = set()

    def _clean_corporate_action_item(
        self,
        item,
        watermark_map: dict,
        default_fields: tuple,
        dedup_field: str = "ex_date",
        known_keys: set = None,
    ):
        item = valmap(lambda x: x[0], item)
        if not item.get("ex_date") or not item.get("report_date"):
            self.logger.debug(f"Missing ex_date or report_date in item: {item}")
            return None

        if not is_valid_ashare_sid(item.get("sid", "")):
            return None

        item["sid"] = encode_sid(item["sid"])
        item["ex_date"] = parse_datetime_to_int(item["ex_date"])
        item["report_date"] = parse_datetime_to_int(item["report_date"])
        item["register_date"] = parse_datetime_to_int(item.get("register_date"))

        for field in default_fields:
            item.setdefault(field, 0)

        dedup_key = (item["sid"], item[dedup_field])
        if dedup_key in self.seen_keys:
            return None

        ex_pair = (item["sid"], item["ex_date"])
        if known_keys:
            # 当数据库已预加载 (sid, ex_date) 集合时，支持晚公告/改期的历史分红补录
            if ex_pair in known_keys:
                return None
            self.seen_keys.add(dedup_key)
            known_keys.add(ex_pair)
            return item

        latest_ex_date = watermark_map.get(item["sid"], 0)
        self.logger.debug(f"Cleaned item: {item}, watermark: {latest_ex_date}")
        if item["ex_date"] > latest_ex_date:
            self.seen_keys.add(dedup_key)
            return item
        return None


class Asset(Pipeline):

    def process_item(self, item, spider):
        item = valmap(lambda x: x[0], item)
        item.setdefault("delist", 0)

        if not is_valid_ashare_sid(item.get("sid", "")):
            raise DropItem("Empty Asset")

        trading_date = parse_trading_date_int(item.get("first_trading"))
        if trading_date <= 0:
            raise DropItem("Empty Asset")

        item["first_trading"] = trading_date
        max_date = spider.asset_latest_date
        if item["first_trading"] > max_date:
            item["sid"] = item["sid"].encode("utf-8")
            item["name"] = item["name"].encode("utf-8")

            self.logger.info(f"Found Asset item: {item}")
            return item
        raise DropItem("Empty Asset")
    

class Adjustment(CorporateActionPipeline):
    """
       xpath of sina adjustment
    """

    def process_item(self, item, spider):
        cleaned = self._clean_corporate_action_item(
            item,
            watermark_map=spider.adj_ex_date,
            default_fields=("bonus_share", "transfer", "bonus"),
            dedup_field="ex_date",
            known_keys=getattr(spider, "adj_known_keys", None),
        )
        if cleaned is not None:
            return cleaned
        raise DropItem("Empty Adjustment")
    

class Rightment(CorporateActionPipeline):
    """
        align item in order to construct frame finally
    """
    def process_item(self, item, spider):
        cleaned = self._clean_corporate_action_item(
            item,
            watermark_map=spider.rgt_ex_date,
            default_fields=("ratio", "price"),
            dedup_field="report_date",
            known_keys=getattr(spider, "rgt_known_keys", None),
        )
        if cleaned is not None:
            return cleaned
        raise DropItem("Empty Rightment")


class AsyncDb(Pipeline):

    _loop = None

    @classmethod
    def from_crawler(cls, crawler):
        instance = cls(
            batch_size=crawler.settings.getint('POSTGRES_BATCH_SIZE', 100),
            max_retry=crawler.settings.getint('POSTGRES_RETRY', 3)
        )
        instance.logger = crawler.spider.logger

        if cls._loop is None:
            cls._loop = _get_reactor_loop()
        
        instance._loop = cls._loop
        return instance

    def __init__(self, batch_size=100, flush_interval=10, max_retry=3):
        self.batch_size = batch_size
        self.max_retry = max_retry
        self.flush_interval = flush_interval
        self.queue = None  # defer to open_spider
        self.buffer = []
        self.logger = None
        self._worker_task = None
        self._stop_signal = object()  # 标识关闭队列
        self._loop = None

    def open_spider(self, spider):
        self.queue = asyncio.Queue()
        self._worker_task = asyncio.run_coroutine_threadsafe(self._consume_loop(spider), self._loop)
        self.logger.info(f"AsyncDb for {spider.name} started with event loop (batch_size={self.batch_size})")

    def process_item(self, item, spider):
        self.logger.debug(f"Processing AsyncDb item: {item}")
        if item:
            self.queue.put_nowait(namedData(spider.table_name, dict(item))) # nonblock put or raise queue.Full
        return item

    async def _flush_batch(self, batches, ops):
        grouped = {}
        for batch in batches:
            grouped.setdefault(batch.table_name, []).append(batch.item)
        for table, rows in grouped.items():
            await ops.on_insert_many(table, rows)

    async def force_flush(self):
        if not self.buffer:
            return
        batches_to_flush = list(self.buffer)
        last_err = None
        for attempt in range(1, self.max_retry + 1):
            try:
                async with async_ops as ops:
                    await self._flush_batch(batches_to_flush, ops)
                del self.buffer[:len(batches_to_flush)]
                return
            except Exception as e:
                last_err = e
                self.logger.warning(
                    f"[AsyncDb] flush attempt {attempt}/{self.max_retry} failed: {e}"
                )
                if attempt < self.max_retry:
                    await asyncio.sleep(min(2 ** attempt, 5))
        # 重试耗尽后清理当前坏批次并记录错误，避免阻塞后续批次消费
        del self.buffer[:len(batches_to_flush)]
        self.logger.error(
            f"[AsyncDb] Dropped {len(batches_to_flush)} items after {self.max_retry} failed flush attempts: {last_err}",
            exc_info=True,
        )

    async def _consume_loop(self, spider):
        while True:
            try:
                data = await asyncio.wait_for(self.queue.get(), timeout=self.flush_interval)
                if data is self._stop_signal:
                    self.logger.info("Received stop signal, exiting consume loop")
                    break

                self.buffer.append(data)

                # 满 batch 大小就 flush
                if len(self.buffer) >= self.batch_size:
                    await self.force_flush()

            except asyncio.TimeoutError:
                try:
                    await self.force_flush()
                except Exception as e:
                    self.logger.error(f"[AsyncDb] Periodic flush error: {e}", exc_info=True)
            except Exception as e:
                self.logger.error(f"[AsyncDb] Consume iteration error: {e}", exc_info=True)

        try:
            await self.force_flush()
        except Exception as e:
            self.logger.error(f"[AsyncDb] Final consume flush error: {e}", exc_info=True)

    def close_spider(self, spider):
        self.logger.info("Closing AsyncDb spider...")

        async def _close():
            try:
                if hasattr(self, '_worker_task') and self._worker_task is not None and not self._worker_task.done():
                    await self.queue.put(self._stop_signal)
                    try:
                        await asyncio.wait_for(
                            asyncio.wrap_future(self._worker_task), 
                            timeout=30.0
                        )
                    except asyncio.TimeoutError:
                        self.logger.warning("Cancel Worker after 30s timeout")
                        self._worker_task.cancel()

                while self.queue and not self.queue.empty():
                    item = self.queue.get_nowait()
                    if item is not self._stop_signal:
                        self.buffer.append(item)

                await self.force_flush()
            except Exception as e:
                self.logger.error(f"Error during close: {e}", exc_info=True)
        
        close_future = asyncio.run_coroutine_threadsafe(_close(), self._loop)
        return Deferred.fromFuture(close_future)


class JsonlFeed(Pipeline):

    def open_spider(self, spider):
        os.makedirs("feeds/jsonl", exist_ok=True)
        time_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.file = open(f"feeds/jsonl/{spider.name}_{time_str}.jsonl", "w", encoding="utf-8")

    def close_spider(self, spider):
        try:
            self.file.close()
        except Exception:
            pass

    def process_item(self, item, spider):
        line = json.dumps(dict(item), cls=CustomFeedJsonEncoder, ensure_ascii=False) + "\n"
        self.file.write(line)
        return item


class ParquetWriter(Pipeline):
    def __init__(self, dataset_root):
        self.dataset_root = dataset_root
        self.buffer = []
        self.partition_cols = ["year", "quarter", "sid", "date"]

    @classmethod
    def from_crawler(cls, crawler):
        instance = cls(
            dataset_root=crawler.settings.get("dataset_root", "data/benchmark")
        )
        instance.logger = crawler.spider.logger
        return instance

    def open_spider(self, spider):
        os.makedirs(self.dataset_root, exist_ok=True)

    def process_item(self, item, spider):
        processed_item = {k: v[0] if isinstance(v, list) else v for k, v in dict(item).items()}
        self.buffer.append(processed_item)
        return item

    def close_spider(self, spider):
        if not self.buffer:
            return

        self.logger.info(f"Scraped {len(self.buffer)} total rows. Starting group-by sid processing...")

        df = pd.DataFrame(self.buffer)
        df = self._prepare_dataframe(df)

        # PyArrow write_dataset group-by sid
        self._write_to_parquet(df, spider.name)
        
        self.buffer = [] 

    def _prepare_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.drop_duplicates(subset=["sid", "tick"], keep="last").copy()
        shanghai_dt = pd.to_datetime(df["tick"]).dt.tz_localize("Asia/Shanghai")
        utc_dt = shanghai_dt.dt.tz_convert("UTC")
 
        df["sid"] = df["sid"].str.replace(r'^[a-zA-Z]+\.|\.[a-zA-Z]+$', '', regex=True)
        df["sid"] = df["sid"].map(index_mapping).fillna(df["sid"])

        # 显式使用秒精度转换，避免不同 pandas 版本 datetime 底层精度(ns/us)差异导致数值错误
        df["tick"] = utc_dt.dt.as_unit("s").astype("int64")
        
        df["year"] = shanghai_dt.dt.year.astype(str)
        df["quarter"] = "Q" + shanghai_dt.dt.quarter.astype(str)
        df["date"] = shanghai_dt.dt.strftime("%Y%m")
        df["datetime"] = utc_dt.dt.tz_localize(None).dt.as_unit("ms") # same with rpc_feed node
        
        numeric_cols = ['open', 'close', 'high', 'low', 'volume', 'amount']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        return df

    def _make_schema(self, df: pd.DataFrame) -> tuple:
        data_fields = []
        for col in df.columns.difference(self.partition_cols):
            if col == "datetime":
                # data_fields.append(pa.field(col, pa.timestamp("ms"))) # default unix utc
                data_fields.append(pa.field(col, pa.timestamp("ms", tz="UTC"))) 
            else:
                data_fields.append(pa.field(col, pa.from_numpy_dtype(df[col].dtype)))
        
        partition_fields = [pa.field(col, pa.string()) for col in self.partition_cols]
        return pa.schema(data_fields + partition_fields), pa.schema(partition_fields)

    def _write_to_parquet(self, df: pd.DataFrame, spider_name: str) -> bool:
        """PyArrow write_dataset group by sid，支持同日增量合并与按日期文件覆盖"""
        try:
            schema, partition_schema = self._make_schema(df)
            trade_dates = (
                df["datetime"]
                .dt.tz_localize("UTC")
                .dt.tz_convert("Asia/Shanghai")
                .dt.strftime("%Y%m%d")
            )
            for trade_date_str, group_df in df.groupby(trade_dates, sort=False):
                basename_template = f"daily_{spider_name}_{trade_date_str}_{{i}}.parquet"
                merged_df = self._merge_existing_daily_parquet(group_df, spider_name, trade_date_str)
                table = pa.Table.from_pandas(merged_df, schema=schema, preserve_index=False)

                ds.write_dataset(
                    data=table,
                    base_dir=self.dataset_root,
                    format="parquet",
                    partitioning=ds.partitioning(partition_schema, flavor="hive"),
                    basename_template=basename_template,
                    existing_data_behavior="overwrite_or_ignore"
                )
        except Exception as e:
            self.logger.error(f"PyArrow Write Error: {e}", exc_info=True)
            raise

    def _merge_existing_daily_parquet(self, df: pd.DataFrame, spider_name: str, trade_date_str: str) -> pd.DataFrame:
        """若目标分区下已存在当日 Parquet 文件，则读取并按 (sid, tick) 增量合并去重。"""
        root_path = Path(self.dataset_root)
        frames = []
        for (year, quarter, sid, date_ym), _ in df.groupby(self.partition_cols, sort=False):
            part_dir = root_path / f"year={year}" / f"quarter={quarter}" / f"sid={sid}" / f"date={date_ym}"
            if part_dir.exists():
                for pq_file in part_dir.glob(f"daily_{spider_name}_{trade_date_str}_*.parquet"):
                    try:
                        old_df = pd.read_parquet(pq_file)
                        old_df["datetime"] = pd.to_datetime(old_df["datetime"]).dt.tz_localize(None).dt.as_unit("ms")
                        old_df["year"] = str(year)
                        old_df["quarter"] = str(quarter)
                        old_df["sid"] = str(sid)
                        old_df["date"] = str(date_ym)
                        frames.append(old_df[df.columns])
                    except Exception as e:
                        self.logger.warning(f"Failed to read existing parquet {pq_file}: {e}")
        if not frames:
            return df
        combined = pd.concat(frames + [df], ignore_index=True)
        return combined.drop_duplicates(subset=["sid", "tick"], keep="last").sort_values("tick").reset_index(drop=True)

