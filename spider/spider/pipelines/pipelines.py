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
import re
import json
import asyncio
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.dataset as ds

from pathlib import Path
from toolz import valmap
from scrapy import signals
# Deferred  to aviod block main thread
from twisted.internet.defer import Deferred
from collections import namedtuple
from sqlalchemy import text
from datetime import datetime
from scrapy.exceptions import DropItem  
from spider.encoder import CustomFeedJsonEncoder

from utils.tools import coerce_to_uint32
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
        crawler.signals.connect(instance.open_spider, signal=signals.spider_opened)
        crawler.signals.connect(instance.close_spider, signal=signals.spider_closed)
        return instance

    def open_spider(self, spider):
        # Initialize resources or connections
        pass

    # core method
    def process_item(self, item, spider):
        # itemloader add_value to return list object
        pass

    def close_spider(self, spider):
        # Clean up resources or connections
        pass


class Asset(Pipeline):

    def process_item(self, item, spider):
        item = valmap(lambda x: x[0], item)
        item.setdefault("delist", 0)

        max_date = spider.asset_latest_date
        if int(item["first_trading"]) > max_date:
            item["sid"] = item["sid"].encode("utf-8")
            item["name"] = item["name"].encode("utf-8")

            self.logger.info(f"Found Asset item: {item}")
            return item
        # return {}
        raise DropItem("Empty Asset")
    

class Adjustment(Pipeline):
    """
       xpath of sina adjustment
    """

    def process_item(self, item, spider):
        item = valmap(lambda x: x[0], item)
        if "ex_date" not in item:
            # not implemented
            self.logger.info(f"Found No Ex_date Adjustment item: {item}")
            # return {} # feeds dict object
            raise DropItem("Empty Adjustment")
    
        m_group = re.match(r'^[630]\d{5}(?:)', item["sid"]) # ?: 非捕获组 只匹配
        if m_group and m_group.group():
            # item["sid"] = item["sid"].split('.')[0]
            item["sid"] = item["sid"].split('.')[0].encode("utf-8")
            item['ex_date'] = int(datetime.strptime(item['ex_date'], '%Y-%m-%d %H:%M:%S').strftime('%Y%m%d'))
            item['report_date'] = int(datetime.strptime(item['report_date'], '%Y-%m-%d %H:%M:%S').strftime('%Y%m%d'))
            
            register_date = item.get("register_date", 0)
            item['register_date'] = int(datetime.strptime(register_date, '%Y-%m-%d %H:%M:%S').strftime('%Y%m%d')) if register_date else 0

            updt = spider.adj_ex_date.get(item["sid"], 0)
            self.logger.info(f"Found Adjustment item: {item} and {updt}")
            if item["ex_date"] > updt:
                return item
        # return {}
        raise DropItem("Empty Adjustment")
    

class Rightment(Pipeline):
    """
        align item in order to construct frame finally
    """
    def process_item(self, item, spider):
        item = valmap(lambda x: x[0], item)
        if "ex_date" not in item:
            self.logger.info(f"Found No Ex_date Rightment item: {item}")
            # return {} 
            raise DropItem("Empty Rightment")

        # item["sid"] = item["sid"].split('.')[0]
        item["sid"] = item["sid"].split('.')[0].encode("utf-8")
        item['report_date'] = int(datetime.strptime(item['report_date'], '%Y-%m-%d %H:%M:%S').strftime('%Y%m%d'))
        item['ex_date'] = int(datetime.strptime(item['ex_date'], '%Y-%m-%d %H:%M:%S').strftime('%Y%m%d'))
        
        register_date = item.get("register_date", 0)
        item['register_date'] = int(datetime.strptime(register_date, '%Y-%m-%d %H:%M:%S').strftime('%Y%m%d')) if register_date else 0
        
        updt = spider.rgt_ex_date.get(item["sid"], 0)
        self.logger.info(f"Found Rightment item: {item} and {updt}")
        if item["ex_date"] > updt:
            return item
        # return {}
        raise DropItem("Empty Rightment")


class AsyncDb(Pipeline):

    _loop = None

    @classmethod
    def from_crawler(cls, crawler):
        instance = cls(
            batch_size=crawler.settings.getint('POSTGRES_BATCH_SIZE', 1),
            max_retry=crawler.settings.getint('POSTGRES_RETRY', 3)
        )
        instance.logger = crawler.spider.logger

        if cls._loop is None:
            cls._loop = _get_reactor_loop()
        
        instance._loop = cls._loop
        return instance

    def __init__(self, batch_size=10, flush_interval=10, max_retry=3):
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
        self.logger.info(f"AsyncDb for {spider.name} started with new event loop")

    def process_item(self, item, spider):
        self.logger.info(f"Processing AsyncDb item: {item}")
        if item:
            self.queue.put_nowait(namedData(spider.table_name, item)) # nonblock put or raise queue.Full
        return item

    async def _flush_batch(self, batches, ops):
        for batch in batches:
            table = batch.table_name
            item = batch.item
            columns = ', '.join(item.keys())
            values = ', '.join([f':{k}' for k in item.keys()])
            sql = text(f"INSERT INTO {table} ({columns}) VALUES ({values})")
            await ops.on_insert(sql, item)

    async def force_flush(self):
        async with async_ops as ops:
            if self.buffer:
                await self._flush_batch(self.buffer, ops)
                self.buffer.clear()

    async def _consume_loop(self, spider):
        try:
            while True:
                try:
                    data = await asyncio.wait_for(self.queue.get(), timeout=self.flush_interval)
                    if data is self._stop_signal:
                        print("Received stop signal, exiting consume loop")
                        break

                    self.buffer.append(data)

                    # 满 batch 大小就 flush
                    if len(self.buffer) >= self.batch_size:
                        await self.force_flush()

                except asyncio.TimeoutError:
                    await self.force_flush()

            await self.force_flush()

        except Exception as e:
            self.logger.error(f"[AsyncDb] Background consume loop failed: {e}", exc_info=True)

    def close_spider(self, spider):
        print("Closing AsyncDb spider...")

        async def _close():
            try:
                if hasattr(self, '_worker_task') and not self._worker_task.done():
                    await self.queue.put(self._stop_signal)
                    try:
                        await asyncio.wait_for(
                            asyncio.wrap_future(self._worker_task), 
                            timeout=10.0
                        )
                    except asyncio.TimeoutError:
                        self.logger.warning("Cancel Worker")
                        self._worker_task.cancel()
                
                await self.force_flush()
            except Exception as e:
                self.logger.error(f"Error during close: {e}")
        
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
        line = json.dumps(dict(item), indent=4, cls=CustomFeedJsonEncoder, ensure_ascii=False) + "\n"
        self.file.write(line)
        return item


class ParquetWriter(Pipeline):
    def __init__(self, dataset_root):
        self.dataset_root = dataset_root
        self.buffer = []
        self.partition_cols = ["year", "quarter", "sid", "date"]

    @classmethod
    def from_crawler(cls, crawler):
        instance =cls(
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
        df["datetime"] = pd.to_datetime(df["tick"]).dt.tz_localize("Asia/Shanghai")
 
        df["sid"] = df["sid"].str.replace(r'^[a-zA-Z]+\.|\.[a-zA-Z]+$', '', regex=True)
        df["sid"] = df["sid"].map(index_mapping).fillna(df["sid"])

        # datetime64[ns, UTC] pandas extensionType --- pd.api.types.is_datetime64_any_dtype ---> int64
        # nosemanic Parquet tick is int64 with Tableau, PowerBI , 1718637195 not 2026-06-17 15:13:15` /pd.to_datetime(df['tick'], unit='s')`
        df["tick"] = (df["datetime"].dt.tz_convert("UTC").astype("int64") // 10**9).astype("int64") 
        # # tick 'datetime64[ns, UTC]' ---> 'datetime64[ns]' which is recgonized by pa.from_numpy_dtype 
        # df["tick"] = df["datetime"].dt.tz_convert("UTC").dt.tz_localize(None)
        
        df["year"] = df["datetime"].dt.year.astype(str)
        df["quarter"] = df["datetime"].apply(lambda x: f'Q{((x.month - 1) // 3) + 1}')
        df["date"] = df["datetime"].dt.strftime("%Y%m")
        df["datetime"] = df["datetime"].dt.tz_convert("UTC").dt.tz_localize(None) # same with rpc_feed node
        
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
        """PyArrow write_dataset group by sid """
        try:
            schema, partition_schema = self._make_schema(df)
            table = pa.Table.from_pandas(df, schema=schema, preserve_index=False)

            now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            basename_template = f"daily_{spider_name}_{now_str}_{{i}}.parquet"

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

