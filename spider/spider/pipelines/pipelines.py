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

import re
import asyncio
import h5py
import numpy as np
import pandas as pd
from toolz import valmap
from scrapy import signals
# Deferred  to aviod block main thread
from twisted.internet.defer import Deferred
from collections import namedtuple
from sqlalchemy import text
from datetime import datetime

from utils.tools import coerce_to_uint32
from utils.operator import async_ops

__all__ = ['Asset', 'Benchmark', 'Adjustment', 'Rightment', 'AsyncDb', 'HDF5Writer']


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

        ipo_date = spider.asset_first_trading
        if int(item["first_trading"]) > ipo_date:
            self.logger.info(f"Found Asset item: {item} and {ipo_date}")
            return item
        return {}
    

class Benchmark(Pipeline):
    
    def process_item(self, item, spider):
        if item:
            item = valmap(lambda x: x[0], item)
            date = int(datetime.strptime(item['date'], '%Y-%m-%d').strftime('%Y%m%d'))
            updt = spider.bench_data.get(item["sid"], 0)
            if date > updt:
                item["date"] = date
                item["open"] = 100 * float(item["open"])
                item["close"] = 100 * float(item["close"])
                item["high"] = 100 * float(item["high"])
                item["low"] = 100 * float(item["low"])
                item["volume"] = int(item["volume"])
                item["amount"] = int(float(item["amount"]))
                self.logger.info(f"Found Adjustment item: {item} and {updt}")
                return item
        return {}


class Adjustment(Pipeline):
    """
       xpath of sina adjustment
    """

    def process_item(self, item, spider):
        item = valmap(lambda x: x[0], item)
        if "ex_date" not in item:
            # not implemented
            self.logger.info(f"Found No Ex_date Adjustment item: {item}")
            return {} # feeds dict object
    
        m_group = re.match(r'^[630]\d{5}(?:)', item["sid"]) # ?: 非捕获组 只匹配
        if m_group.group():
            item["sid"] = item["sid"].split('.')[0]
            item['ex_date'] = int(datetime.strptime(item['ex_date'], '%Y-%m-%d %H:%M:%S').strftime('%Y%m%d'))
            item['report_date'] = int(datetime.strptime(item['report_date'], '%Y-%m-%d %H:%M:%S').strftime('%Y%m%d'))
            
            register_date = item.get("register_date", 0)
            item['register_date'] = int(datetime.strptime(register_date, '%Y-%m-%d %H:%M:%S').strftime('%Y%m%d')) if register_date else 0
            updt = spider.adj_ex_date.get(item["sid"], 0)
            self.logger.info(f"Found Adjustment item: {item} and {updt}")
            if item["ex_date"] > updt:
                return item
        return {}
    

class Rightment(Pipeline):
    """
        align item in order to construct frame finally
    """
    def process_item(self, item, spider):
        item = valmap(lambda x: x[0], item)
        if "ex_date" not in item:
            self.logger.info(f"Found No Ex_date Rightment item: {item}")
            return {} 

        item["sid"] = item["sid"].split('.')[0]
        item['report_date'] = int(datetime.strptime(item['report_date'], '%Y-%m-%d %H:%M:%S').strftime('%Y%m%d'))
        item['ex_date'] = int(datetime.strptime(item['ex_date'], '%Y-%m-%d %H:%M:%S').strftime('%Y%m%d'))
        
        register_date = item.get("register_date", 0)
        item['register_date'] = int(datetime.strptime(register_date, '%Y-%m-%d %H:%M:%S').strftime('%Y%m%d')) if register_date else 0
        
        updt = spider.rgt_ex_date.get(item["sid"], 0)
        self.logger.info(f"Found Rightment item: {item} and {updt}")
        if item["ex_date"] > updt:
            return item
        return {}


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
        # avoid attached to a different loop
            try:
                cls._loop = asyncio.get_event_loop()
            except RuntimeError:
                cls._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(cls._loop)
        
        instance._loop = cls._loop
        return instance

    def __init__(self, batch_size=10, flush_interval=10, max_retry=3):
        self.batch_size = batch_size
        self.max_retry = max_retry
        self.flush_interval = flush_interval
        self.queue = asyncio.Queue() # asyncio.lock
        self.buffer = []
        self.logger = None
        self._worker_task = None
        self._stop_signal = object()  # 标识关闭队列
        self._loop = None

    def open_spider(self, spider):
        # 启动后台消费者任务 / concurrent.futures.Future object
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
        
        # 执行关闭
        close_future = asyncio.run_coroutine_threadsafe(_close(), self._loop)
        return Deferred.fromFuture(close_future)
    

class CsvWriter(Pipeline):
    def __init__(self, filename):
        self.filename = filename
        self.file = open(filename, 'w')
        
    def process_item(self, item, spider):
        self.file.write(item)


class HDF5Writer(Pipeline):
    """
    Class capable of writing daily OHLCV data to disk in a format that
    can be read efficiently by HDF5DailyBarReader.

    Parameters
    ----------
    filename : str
        The location at which we should write our output.
    date_chunk_size : int
        The number of days per chunk in the HDF5 file. If this is
        greater than the number of days in the data, the chunksize will
        match the actual number of days.

    See Also
    --------
    zipline.data.hdf5_daily_bars.HDF5DailyBarReader
    """
    VERSION = 0

    DATA = 'data'
    # INDEX = 'index'
    SCALING_FACTOR = 'scaling_factor'

    OPEN = 'open'
    HIGH = 'high'
    LOW = 'low'
    CLOSE = 'close'
    VOLUME = 'volume'

    FIELDS = (OPEN, HIGH, LOW, CLOSE, VOLUME)

    DEFAULT_SCALING_FACTORS = {
        # Retain 3 decimal places for prices.
        OPEN: 1000,
        HIGH: 1000,
        LOW: 1000,
        CLOSE: 1000,
        # Volume is expected to be a whole integer.
        VOLUME: 1,
    }

    def __init__(self, filename, date_chunk_size):
        self._filename = filename
        self._date_chunk_size = date_chunk_size

    def h5_file(self, mode):
        return h5py.File(self._filename, mode)

    def write(self,
              field,
              frames,
              scaling_factors=None):
        """
        Write the OHLCV data for one country to the HDF5 file.

        Parameters
        ----------
        frames : dict[str, pd.DataFrame]
            A dict mapping each OHLCV field to a dataframe with a row
            for each date and a column for each sid. The dataframes need
            to have the same index and columns.
        scaling_factors : dict[str, float], optional
            A dict mapping each OHLCV field to a scaling factor, which
            is applied (as a multiplier) to the values of field to
            efficiently store them as uint32, while maintaining desired
            precision. These factors are written to the file as metadata,
            which is consumed by the reader to adjust back to the original
            float values. Default is None, in which case
            DEFAULT_SCALING_FACTORS is used.
        """
        if scaling_factors is None:
            scaling_factors = self.DEFAULT_SCALING_FACTORS

        with self.h5_file(mode='a') as h5_file:
            # ensure that the file version has been written
            h5_file.attrs['version'] = self.VERSION

            # self._write_index_group(country_group, days, sids)
            field_group = h5_file.create_group(field)
            # sub_group
            self._write_data_group(
                field_group,
                frames,
                scaling_factors,
                chunks=None,
            )

    def write_from_sid_df_pairs(self,
                                field_code,
                                data,
                                currency_codes=None,
                                scaling_factors=None):
        """
        Parameters
        ----------
        country_code : str
            The ISO 3166 alpha-2 country code for this country.
        data : iterable[tuple[int, pandas.DataFrame]]
            The data chunks to write. Each chunk should be a tuple of
            sid and the data for that asset.
        currency_codes : pd.Series, optional
            Series mapping sids to 3-digit currency code values for those sids'
            listing currencies. If not passed, missing currencies will be
            written.
        scaling_factors : dict[str, float], optional
            A dict mapping each OHLCV field to a scaling factor, which
            is applied (as a multiplier) to the values of field to
            efficiently store them as uint32, while maintaining desired
            precision. These factors are written to the file as metadata,
            which is consumed by the reader to adjust back to the original
            float values. Default is None, in which case
            DEFAULT_SCALING_FACTORS is used.
        """
        data = list(data)
        if not data:
            empty_frame = pd.DataFrame(
                data=None,
                index=np.array([], dtype='datetime64[ns]'),
                columns=np.array([], dtype='int64'),
            )
            return self.write(
                {f: empty_frame.copy() for f in self.FIELDS},
                scaling_factors,
            )

        sids, frames = zip(*data)
        ohlcv_frame = pd.concat(frames)

        # Repeat each sid for each row in its corresponding frame.
        sid_ix = np.repeat(sids, [len(f) for f in frames])

        # Add id to the index, so the frame is indexed by (date, id).
        ohlcv_frame.set_index(sid_ix, append=True, inplace=True)

        frames = {
            field: ohlcv_frame[field].unstack()
            for field in self.FIELDS
        }

        return self.write(
            field_code,
            frames=frames,
            scaling_factors=scaling_factors,
        )

    def _write_data_group(self,
                          field_group,
                          frames,
                          scaling_factors,
                          chunks):
        """Write /country/data
        """
        data_group = field_group.create_group(self.DATA)

        for field in self.FIELDS:
            frame = frames[field]

            # Sort rows by increasing sid, and columns by increasing date.
            frame.sort_index(inplace=True)
            frame.sort_index(axis='columns', inplace=True)

            data = coerce_to_uint32(
                frame.T.fillna(0).values,
                scaling_factors[field],
            )

            dataset = data_group.create_dataset(
                field,
                compression='lzf',
                shuffle=True,
                data=data,
                chunks=chunks,
            )
            dataset.attrs[self.SCALING_FACTOR] = scaling_factors[field]

    def process_item(self, item, spider):
        owner = item['owner'][0]
        self.write(owner,item)
