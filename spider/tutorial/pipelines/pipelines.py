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

import asyncio
import h5py
import numpy as np
import pandas as pd
from toolz import valmap
from scrapy import signals
from twisted.internet.defer import Deferred
from collections import defaultdict
from sqlalchemy import text

from tutorial.utils.tools import coerce_to_uint32
from tutorial.utils.operator import async_ops

__all__ = ['Asset', 'Adjustment', 'Rightment', 'AsyncDb', 'HDF5Writer']


class Pipeline:
    """
        enroll into mysql according to owner sid item
    """

    @classmethod
    def from_crawler(cls, crawler):
        instance = cls()
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
        if item:
            item = valmap(lambda x: x[0], item)
            item.setdefault("delist", 0)
        return item


class Basics(Pipeline):
    """
        align item in order to construct frame finally
    """
    def process_item(self, item, spider):
        if item:
            item = valmap(lambda x: [(',').join(x)], item)
        return item
    

class Adjustment(Pipeline):
    """
       xpath of sina adjustment
    """

    def process_item(self, item, spider):
        if item:
            sid = item.pop('sid')
            nums = valmap(lambda x: int(len(x) / len(sid)), item)
            times = set(nums.values())
            item['sid'] = list(np.tile(sid, times.pop()))
        return item
    

class Rightment(Pipeline):
    """
        align item in order to construct frame finally
    """
    def process_item(self, item, spider):
        if item:
            pass


class AsyncDb(Pipeline):

    def __init__(self, batch_size=1, max_retry=3):
        self.batch_size = batch_size
        self.max_retry = max_retry
        self.buffer = defaultdict(list)
        self.logger = None

    @classmethod
    def from_crawler(cls, crawler):
        batch_size = crawler.settings.getint('POSTGRES_BATCH_SIZE', 1)
        max_retry = crawler.settings.getint('POSTGRES_RETRY', 3)
        instance = cls(batch_size, max_retry)
        instance.logger = crawler.spider.logger
        return instance

    def process_item(self, item, spider):
        if not item:
            return item
            
        self.buffer[spider.table_name].append(item)
        if len(self.buffer[spider.table_name]) >= self.batch_size:
            return Deferred.fromFuture(
                asyncio.run_coroutine_threadsafe(self._flush_buffer(spider), asyncio.get_event_loop())
            )
        return item

    async def _flush_buffer(self, spider):
        try:
            async with async_ops as ops:
                await ops.initialize(spider.crawler)
                for table_name, items in self.buffer.items():
                    for item in items:
                        # 构建 INSERT 语句
                        columns = ', '.join(item.keys())
                        values = ', '.join([f':{k}' for k in item.keys()])
                        sql = text(f"INSERT INTO {table_name} ({columns}) VALUES ({values})")
                        await ops.on_insert(sql, item)
            self.buffer.clear()
        except Exception as e:
            self.logger.error(f"Insert failed: {e}")
            await self._retry_insert(spider)
        return self.buffer

    async def _retry_insert(self, spider):
        for attempt in range(self.max_retry):
            try:
                async with async_ops as ops:
                    await ops.initialize(spider.crawler)
                    for table_name, items in self.buffer.items():
                        for item in items:
                            columns = ', '.join(item.keys())
                            values = ', '.join([f':{k}' for k in item.keys()])
                            sql = text(f"INSERT INTO {table_name} ({columns}) VALUES ({values})")
                            await ops.on_insert(sql, item)
                self.buffer.clear()
                return
            except Exception as e:
                self.logger.error(f"Retry {attempt + 1} failed: {e}")
                if attempt == self.max_retry - 1:
                    self.logger.error("Max retry reached. Dropping items.")
                    self.buffer.clear()

    def close_spider(self, spider):
        if self.buffer:
            asyncio.create_task(self._flush_buffer(spider))
        asyncio.create_task(async_ops.cleanup())


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
