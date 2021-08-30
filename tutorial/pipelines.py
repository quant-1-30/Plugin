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

import pandas as pd, numpy as np
from .db import get_db_con
from .models import metadata
from toolz import valmap


class TutorialPipeline:
    """
        enroll into mysql according to owner sid item
    """

    @classmethod
    def from_crawler(cls, crawler):
        # return pipeline instance
        return cls

    def open_spider(self, spider):
        pass

    def process_item(self, item, spider):
        pass

    def close_spider(self, spider):
        pass


class BasicsPipeline:
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


class AlignPipeline:
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


class DbPipeline:
    """
        enroll into mysql according to owner sid item
    """
    @classmethod
    def from_crawler(cls, crawler):
        init = crawler.settings.getbool('Initialize')
        return cls(init)

    def __init__(self, mode):
        self.init = mode
        self.con = None

    def open_spider(self, spider):
        self.con = get_db_con()

    def process_item(self, item, spider):
        if item:
            # init = item.pop('initialize')
            tbl = item.pop('owner')[0]
            table = metadata.tables[tbl]
            frame = pd.DataFrame(item)
            if tbl == 'ownership':
                frame.drop_duplicates(inplace=True, keep='first')
                frame = frame.iloc[1:, :]
            # enroll into database
            params = tuple(frame.T.to_dict().values())
            if self.init:
                self.con.execute(table.insert(), params)
            else:
                from sqlalchemy.dialects.mysql import insert
                # upinsert --- insert if not int or update
                for p in params:
                    insert_stmt = insert(table).values(**p)
                    on_duplicate_key_stmt = insert_stmt.on_duplicate_key_update(**p)
                    self.con.execute(on_duplicate_key_stmt)

    def close_spider(self, spider):
        self.con.close()


# from twisted.enterprise import adbapi
# from pymysql import cursors
# from sqlalchemy.dialects.mysql import insert
#
#
# class DbPipeline:
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

