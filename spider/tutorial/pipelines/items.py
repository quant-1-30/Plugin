# -*- coding: utf-8 -*-
"""
Created on Tue Mar 12 15:37:47 2019

@author: python
"""

# This package will contain the spiders of your Scrapy project
#
# Please refer to the documentation for information on how to create and manage
# your spiders.
# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

from scrapy.item import Item, Field


class AssetItem(Item):

    # 代码
    sid = Field()
    # 中文
    name = Field()
    # ipo_date
    first_trading = Field()


class KlineItem(Item):
    # 代码
    sid = Field()
    # 日期
    date = Field()
    # 开盘价
    open = Field()
    # 收盘价
    close = Field()
    # 最高价
    high = Field()
    # 最低价
    low = Field()


class Dividend(Item):

    # 代码
    sid = Field()
    # 报告日期
    report_date = Field()
    # 股权登记日
    register_date = Field()
    # 除权除息日
    ex_date = Field()
    # # 红股上市日
    # market_date = Field()
    # 送股(每10股)
    bonus_share = Field()
    # 转增(每10股)
    transfer = Field()
    # 派息(税前)(元)
    bonus = Field()
    # # 进度
    # progress = Field()


class Right(Item):

    # 代码
    sid = Field()
    # 报告日期
    report_date = Field()
    # 股权登记日
    register_date = Field()
    # 除权日
    ex_date = Field()
    # # 配股上市日
    # market_date = Field()
    # 配股方案
    ratio = Field()
    # 配股价格(元)
    price = Field()
    