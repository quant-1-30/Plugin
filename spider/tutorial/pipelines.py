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

import h5py
import numpy as np
import pandas as pd
from toolz import valmap
from functools import partial
from scrapy import signals


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

    def process_item(self, item, spider):
        pass

    def close_spider(self, spider):
        # Clean up resources or connections
        pass


class BasicsInfo(Pipeline):
    """
        align item in order to construct frame finally
    """

    def process_item(self, item, spider):
        if item:
            item = dict(item)
            owner = item['owner'][0]
            if owner == 'basics':
                item = valmap(lambda x: [(',').join(x)], item)
        return item


class Adjustment(Pipeline):
    """
        align item in order to construct frame finally
    """
    def process_item(self, item, spider):
        if item:
            owner = item['owner'][0]
            if owner in ['dividends', 'rights', 'ownership']:
                sid = item.pop('sid')
                owner = item.pop('owner')
                nums = valmap(lambda x: int(len(x) / len(sid)), item)
                times = set(nums.values())
                item['sid'] = list(np.tile(sid, times.pop()))
                item['owner'] = owner
        return item





def coerce_to_uint32(a, scaling_factor):
    """
    Returns a copy of the array as uint32, applying a scaling factor to
    maintain precision if supplied.
    """
    return (a * scaling_factor).round().astype('uint32')


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

    # DAY = 'day'
    # SID = 'sid'

    # START_DATE = 'start_date'
    # END_DATE = 'end_date'

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

        # Note that this functions validates that all of the frames
        # share the same days and sids.
        # days, sids = days_and_sids_for_frames(list(frames.values()))


        # # Write start and end dates for each sid.
        # start_date_ixs, end_date_ixs = compute_asset_lifetimes(frames)

        # if len(sids):
        #     chunks = (len(sids), min(self._date_chunk_size, len(days)))
        # else:
        #     # h5py crashes if we provide chunks for empty data.
        #     chunks = None

        with self.h5_file(mode='a') as h5_file:
            # ensure that the file version has been written
            h5_file.attrs['version'] = self.VERSION

            # self._write_index_group(country_group, days, sids)
            field_group = h5_file.create_group(field)
            # sub_group
            
            # self._write_index_group(field_group, days, sids)

            # self._write_lifetimes_group(
            #     field_group,
            #     start_date_ixs,
            #     end_date_ixs,
            # )
            
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

    # def _write_index_group(self, days, sids):
    #     """Write /country/index.
    #     """
    #     index_group = country_group.create_group(INDEX)
    #     self._log_writing_dataset(index_group)

    #     index_group.create_dataset(SID, data=sids)

    #     # h5py does not support datetimes, so they need to be stored
    #     # as integers.
    #     index_group.create_dataset(DAY, data=days.astype(np.int64))

    # def _write_lifetimes_group(self,
    #                            country_group,
    #                            start_date_ixs,
    #                            end_date_ixs):
    #     """Write /country/lifetimes
    #     """
    #     lifetimes_group = country_group.create_group(LIFETIMES)
    #     self._log_writing_dataset(lifetimes_group)

    #     lifetimes_group.create_dataset(START_DATE, data=start_date_ixs)
    #     lifetimes_group.create_dataset(END_DATE, data=end_date_ixs)

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


# def init_engine():
#     # 在这里导入定义模型所需要的所有模块，这样它们就会正确的注册在
#     # 元数据上。否则你就必须在调用 init_db() 之前导入它们, import --- 执行脚本
#     # scoped_session 线程安全
#     # from sqlalchemy.orm import sessionmaker, scoped_session
#     # db_session = scoped_session(sessionmaker(autocommit=False,
#     #                                          autoflush=False,
#     #                                          bind=engine))
#     # from sqlalchemy.ext.declarative import declarative_base
#     # Base = declarative_base()
#     # Base.query = db_session.query_property()
#     # Base.metadata.create_all(bind=engine)
#     engine_path = 'mysql+pymysql://{username}:{password}@{host}:{port}'.format(**MYSQL)
#     eng = create_engine(engine_path, pool_size=MYSQL['pool_size'],
#                         max_overflow=MYSQL['max_overflow'])
#     create_str = "CREATE DATABASE IF NOT EXISTS %s ;" % MYSQL['db']
#     eng.execute(create_str)
#     eng.execute("use %s" % MYSQL['db'])
#     # engine_path = 'mysql+pymysql://{username}:{password}@{host}:{port}/{db}'.format(**MYSQL)
#     # eng = create_engine(engine_path, pool_size=MYSQL['pool_size'],
#     #                     max_overflow=MYSQL['max_overflow'])
#     return eng


# from twisted.enterprise import adbapi
# from pymysql import cursors
# from sqlalchemy.dialects.mysql import insert
#
#
# class Writer(Pipeline):
#     """
#         enroll into mysql according to owner sid item
#     """
#     def __init__(self, db_pool):
#         self.db_pool = db_pool
#
#     @classmethod
#     def from_crawler(cls, crawler):
#         settings = crawler.settings.get('MYSQL')
#         db_params = dict(
#             host=settings['host'],
#             user=settings['username'],
#             password=settings['password'],
#             port=settings['port'],
#             db=settings['db'],
#             use_unicode=True,
#             cursorclass=cursors.Cursor
#         )
#         db_pool = adbapi.ConnectionPool('pymysql', **db_params)
#         return cls(db_pool)
#
#     def process_item(self, item, spider):
#         query = self.db_pool.runInteraction(self.insert_item, item)
#
#     def insert_item(self, cursor, item):
#         if item:
#             tbl = item.pop('table')[0]
#             frame = pd.DataFrame(item)
#             if tbl == 'ownership':
#                 frame.drop_duplicates(inplace=True, keep='first')
#                 frame = frame.iloc[1:, :]
#             # enroll into database
#             params = tuple(frame.T.to_dict().values())
#             table = metadata.tables[tbl]
#             print('params', params)
#             for p in params:
#                 cursor.execute(str(table.insert()), p)
#                 # insert_stmt = insert(table).values(**p)
#                 # on_duplicate_key_stmt = insert_stmt.on_duplicate_key_update(**p)
#                 # print('sql', str(on_duplicate_key_stmt))
#                 # cursor.execute(str(on_duplicate_key_stmt))

