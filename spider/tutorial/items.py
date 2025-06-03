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


# 可转债信息
class BondItem(Item):

    # 债券代码
    sid = Field()
    # 中文
    name = Field()
    # 正股代码
    swap_code = Field()
    # 转股价
    swap_price = Field()
    # 转股开始日期
    swap_sdate = Field()
    # 转股结束日期
    swap_edate = Field()


# dual
class DualItem(Item):

    # sid
    sid = Field()
    # name
    name = Field()
    # hk code
    dual = Field()



class BasicsItem(Item):

    # 代码
    sid = Field()
    # 公司名称
    name = Field()
    # 上市市场
    market = Field()
    # 上市日期
    ipo_date = Field()
    # 发行价格
    ipo_price = Field()
    # 主承销商
    broker = Field()
    # 邮政编码
    district_code = Field()


class Dividend(Item):

    # 代码
    sid = Field()
    # # 公告日期
    # declare_date = Field()
    # 股权登记日
    register_date = Field()
    # 除权除息日
    ex_date = Field()
    # # 红股上市日
    # market_date = Field()
    # 送股(股)
    bonus_share = Field()
    # 转增(股)
    transfer = Field()
    # 派息(税前)(元)
    bonus = Field()
    # # 分红方案(每10股)
    # divdend_plan = Field()
    # # 进度
    # progress = Field()


    # sid: Mapped[str] = mapped_column(String(20), 
    #                                  ForeignKey("asset.sid", onupdate="CASCADE", ondelete="CASCADE"), 
    #                                  nullable=False, use_existing_column=True)
    # register_date: Mapped[int] = mapped_column(Integer, nullable=False, use_existing_column=True)
    # ex_date: Mapped[int] = mapped_column(Integer, nullable=False, use_existing_column=True)
    # share: Mapped[int] = mapped_column(Integer, nullable=True, use_existing_column=True)
    # transfer: Mapped[int] = mapped_column(Integer, nullable=True, use_existing_column=True)
    # interest: Mapped[int] = mapped_column(Integer, nullable=True, use_existing_column=True)


class Right(Item):

    # 代码
    sid = Field()
    # # 公告日期
    # declare_date = Field()
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
    # # 基准股本(股)
    # base = Field()
    

    # id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # sid: Mapped[str] = mapped_column(String(20), 
    #                                  ForeignKey("asset.sid", onupdate="CASCADE", ondelete="CASCADE"), 
    #                                  nullable=False, primary_key=True, use_existing_column=True)
    # register_date: Mapped[int] = mapped_column(Integer, nullable=False, use_existing_column=True)
    # ex_date: Mapped[int] = mapped_column(Integer, nullable=False, use_existing_column=True)
    # # effective_date: Mapped[int] = mapped_column(Integer, nullable=False, use_existing_column=True)
    # price: Mapped[int] = mapped_column(Integer, nullable=True, use_existing_column=True)
    # ratio: Mapped[int] = mapped_column(Integer, nullable=True, use_existing_column=True)

# 股权结构
class Ownership(Item):

    # 代码
    sid = Field()
    # 变动日期
    change_date = Field()
    # 总股本
    general = Field()
    # 流通A股
    float = Field()
    # 限售A股
    strict = Field()


# kline
class KlineItem(Item):

    # 代码
    sid = Field()
    # 交易日
    trade_dt = Field()
    open = Field()
    close = Field()
    high = Field()
    low = Field()
    volume = Field()
    amount = Field()
    amplitude = Field()
    pct = Field()
    change = Field()
    turnover = Field()
