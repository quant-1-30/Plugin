# !/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Mar 12 15:37:47 2019

@author: python
"""
import sqlalchemy as sa
from sqlalchemy.sql import func
from sqlalchemy import MetaData
from .db import engine

metadata = MetaData(bind=engine)

# autoincrement : The setting only has an effect for columns which are:
#
# Integer derived (i.e. INT, SMALLINT, BIGINT).
#
# Part of the primary key
#
# Not referring to another column via ForeignKey, unless the value is specified as 'ignore_fk':

# stock assets id autoincrement but not primary key
equity = sa.Table(
    'equity',
    metadata,
    # sa.Column(
    #     'id',
    #     sa.Integer,
    #     index=True,
    #     unique=True,
    #     autoincrement=True,
    #     primary_key=True,
    # ),
    sa.Column(
        'sid',
        sa.String(10),
        index=True,
        unique=True,
        nullable=False,
        primary_key=True,
    ),
    sa.Column(
        'name',
        sa.Text,
        nullable=False,
    ),
    extend_existing=False,
)


# convertible bond assets , 主要考虑流动性和折价空间, 回售2年70%，赎回130% ，但是可以没回售条款比如金融行业（中行)
bond = sa.Table(
    'bond',
    metadata,
    # sa.Column(
    #     'id',
    #     sa.Integer,
    #     index=True,
    #     primary_key=True,
    #     autoincrement=True
    # ),
    sa.Column(
        'sid',
        sa.String(10),
        index=True,
        unique=True,
        nullable=False,
        primary_key=True
    ),
    sa.Column(
        'name',
        sa.String(30),
        nullable=False,
    ),
    sa.Column(
        'swap_code',
        sa.String(10),
        nullable=False,
        primary_key=True
    ),
    sa.Column(
        'swap_price',
        sa.String(5),
        nullable=False

    ),
    sa.Column(
        'swap_sdate',
        sa.String(20),
        nullable=False
    ),
    sa.Column(
        'swap_edate',
        sa.String(20),
        nullable=False
    ),
    extend_existing=True
)

# exchange of fund assets
fund = sa.Table(
    'fund',
    metadata,
    # sa.Column(
    #     'id',
    #     sa.Integer,
    #     index=True,
    #     primary_key=True,
    #     autoincrement=True
    # ),
    sa.Column(
        'sid',
        sa.String(10),
        index=True,
        unique=True,
        nullable=False,
        primary_key=True
    ),
    sa.Column(
        'name',
        sa.String(20),
        nullable=False,
    ),
    extend_existing=True
)

# benchmark
bench = sa.Table(
    'bench',
    metadata,
    # sa.Column(
    #     'id',
    #     sa.Integer,
    #     index=True,
    #     primary_key=True,
    #     autoincrement=True
    # ),
    sa.Column(
        'sid',
        sa.String(10),
        index=True,
        unique=True,
        nullable=False,
        primary_key=True
    ),
    sa.Column(
        'name',
        sa.String(20),
        nullable=False,
    ),
    extend_existing=True
)


duals = sa.Table(
    'duals',
    metadata,
    # sa.Column(
    #     'id',
    #     sa.Integer,
    #     index=True,
    #     primary_key=True,
    #     autoincrement=True
    # ),
    # hk code
    sa.Column(
        'sid',
        sa.String(10),
        index=True,
        unique=True,
        nullable=False,
        primary_key=True
    ),
    sa.Column(
        'dual',
        sa.String(10),
        sa.ForeignKey(equity.c.sid, onupdate='CASCADE', ondelete='CASCADE'),
        unique=True,
        nullable=False,
        primary_key=True,
    ),
    sa.Column(
        'name',
        sa.Text,
        nullable=False,
    ),
    extend_existing=False,
)


# stock daily kline
equity_price = sa.Table(
    'equity_price',
    metadata,
    # sa.Column(
    #     'id',
    #     sa.Integer,
    #     index=True,
    #     # primary_key=True,
    #     autoincrement=True
    # ),
    sa.Column(
        'sid',
        sa.String(10),
        # 外键更新与删除自动关联
        sa.ForeignKey(equity.c.sid, onupdate='CASCADE', ondelete='CASCADE'),
        nullable=False,
        primary_key=True,
    ),
    sa.Column(
        'trade_dt',
        sa.String(10),
        nullable=False,
        primary_key=True,
    ),
    sa.Column(
        'open',
        sa.Numeric(10, 5),
        nullable=False
    ),
    sa.Column(
        'close',
        sa.Numeric(10, 5),
        nullable=False
    ),
    sa.Column(
        'high',
        sa.Numeric(10, 5),
        nullable=False
    ),
    sa.Column(
        'low',
        sa.Numeric(10, 5),
        nullable=False
    ),
    sa.Column(
        'volume',
        sa.Integer,
        nullable=False
    ),
    sa.Column(
        'amount',
        sa.Numeric(20, 5),
        nullable=False
    ),
    # 振幅
    sa.Column(
        'amplitude',
        sa.Numeric(10, 2),
        nullable=False
    ),
    # 涨跌幅
    sa.Column(
        'pct',
        sa.Numeric(10, 5),
        nullable=False
    ),
    # 涨跌额
    sa.Column(
        'change',
        sa.Numeric(10, 5),
        nullable=False
    ),
    # 换手率
    sa.Column(
        'turnover',
        sa.Numeric(10, 2),
        nullable=False
    ),
    extend_existing=True
)

# bond kline
bond_price = sa.Table(
    'bond_price',
    metadata,
    # sa.Column(
    #     'id',
    #     sa.Integer,
    #     index=True,
    #     # primary_key=True,
    #     autoincrement=True
    # ),
    sa.Column(
        'sid',
        sa.String(10),
        sa.ForeignKey(bond.c.sid, onupdate='CASCADE', ondelete='CASCADE'),
        nullable=False,
        primary_key=True,
    ),
    sa.Column(
        'trade_dt',
        sa.String(10),
        nullable=False,
        primary_key=True
    ),
    sa.Column(
        'open',
        sa.Numeric(10, 5),
        nullable=False
    ),
    sa.Column(
        'high',
        sa.Numeric(10, 5),
        nullable=False
    ),
    sa.Column(
        'low',
        sa.Numeric(10, 5),
        nullable=False
    ),
    sa.Column(
        'close',
        sa.Numeric(10, 5),
        nullable=False
    ),
    sa.Column(
        'volume',
        sa.Integer,
        nullable=False
    ),
    sa.Column(
        'amount',
        sa.Numeric(20, 5),
        nullable=False
    ),
    # 振幅
    sa.Column(
        'amplitude',
        sa.Numeric(10, 2),
        nullable=False
    ),
    # 涨跌幅
    sa.Column(
        'pct',
        sa.Numeric(10, 5),
        nullable=False
    ),
    # 涨跌额
    sa.Column(
        'change',
        sa.Numeric(10, 5),
        nullable=False
    ),
    # 换手率
    sa.Column(
        'turnover',
        sa.Numeric(10, 2),
        nullable=False
    ),
    extend_existing=True
)

# fund kline
fund_price = sa.Table(
    'fund_price',
    metadata,
    # sa.Column(
    #     'id',
    #     sa.Integer,
    #     index=True,
    #     # primary_key=True,
    #     autoincrement=True
    # ),
    sa.Column('sid',
              sa.String(10),
              sa.ForeignKey(fund.c.sid, onupdate='CASCADE', ondelete='CASCADE'),
              nullable=False,
              primary_key=True,
              ),
    sa.Column(
        'trade_dt',
        sa.String(10),
        nullable=False,
        primary_key=True
    ),
    sa.Column(
        'open',
        sa.Numeric(10, 5),
        nullable=False
    ),
    sa.Column(
        'high',
        sa.Numeric(10, 5),
        nullable=False
    ),
    sa.Column(
        'low',
        sa.Numeric(10, 5),
        nullable=False
    ),
    sa.Column(
        'close',
        sa.Numeric(10, 5),
        nullable=False
    ),
    sa.Column(
        'volume',
        sa.Integer,
        nullable=False
    ),
    sa.Column(
        'amount',
        sa.Numeric(20, 5),
        nullable=False
    ),
    # 振幅
    sa.Column(
        'amplitude',
        sa.Numeric(10, 2),
        nullable=False
    ),
    # 涨跌幅
    sa.Column(
        'pct',
        sa.Numeric(10, 5),
        nullable=False
    ),
    # 涨跌额
    sa.Column(
        'change',
        sa.Numeric(10, 5),
        nullable=False
    ),
    # 换手率
    sa.Column(
        'turnover',
        sa.Numeric(10, 2),
        nullable=False
    ),
    extend_existing=True
)


# stock daily kline
duals_price = sa.Table(
    'duals_price',
    metadata,
    # sa.Column(
    #     'id',
    #     sa.Integer,
    #     index=True,
    #     # primary_key=True,
    #     autoincrement=True
    # ),
    sa.Column(
        'sid',
        sa.String(10),
        # 外键更新与删除自动关联
        sa.ForeignKey(duals.c.sid, onupdate='CASCADE', ondelete='CASCADE'),
        nullable=False,
        primary_key=True,
    ),
    sa.Column(
        'trade_dt',
        sa.String(10),
        nullable=False,
        primary_key=True,
    ),
    sa.Column(
        'open',
        sa.Numeric(10, 5),
        nullable=False
    ),
    sa.Column(
        'close',
        sa.Numeric(10, 5),
        nullable=False
    ),
    sa.Column(
        'high',
        sa.Numeric(10, 5),
        nullable=False
    ),
    sa.Column(
        'low',
        sa.Numeric(10, 5),
        nullable=False
    ),
    sa.Column(
        'volume',
        sa.Integer,
        nullable=False
    ),
    sa.Column(
        'amount',
        sa.Numeric(20, 5),
        nullable=False
    ),
    # 振幅
    sa.Column(
        'amplitude',
        sa.Numeric(10, 2),
        nullable=False
    ),
    # 涨跌幅
    sa.Column(
        'pct',
        sa.Numeric(10, 5),
        nullable=False
    ),
    # 涨跌额
    sa.Column(
        'change',
        sa.Numeric(10, 5),
        nullable=False
    ),
    # 换手率
    sa.Column(
        'turnover',
        sa.Numeric(10, 2),
        nullable=False
    ),
    extend_existing=True
)


# benchmark kline
bench_price = sa.Table(
    'bench_price',
    metadata,
    # sa.Column(
    #     'id',
    #     sa.Integer,
    #     index=True,
    #     primary_key=True,
    #     autoincrement=True
    # ),
    sa.Column('sid',
              sa.String(10),
              sa.ForeignKey(bench.c.sid, onupdate='CASCADE', ondelete='CASCADE'),
              nullable=False,
              primary_key=True,
              ),
    sa.Column(
        'trade_dt',
        sa.String(10),
        nullable=False,
        primary_key=True
    ),
    sa.Column(
        'open',
        sa.Numeric(10, 5),
        nullable=False
    ),
    sa.Column(
        'high',
        sa.Numeric(10, 5),
        nullable=False
    ),
    sa.Column(
        'low',
        sa.Numeric(10, 5),
        nullable=False
    ),
    sa.Column(
        'close',
        sa.Numeric(10, 5),
        nullable=False
    ),
    sa.Column(
        'volume',
        sa.Integer,
        nullable=False
    ),
    sa.Column(
        'amount',
        sa.Numeric(20, 5),
        nullable=False
    ),
    # 振幅
    sa.Column(
        'amplitude',
        sa.Numeric(10, 2),
        nullable=False
    ),
    # 涨跌幅
    sa.Column(
        'pct',
        sa.Numeric(10, 5),
        nullable=False
    ),
    # 涨跌额
    sa.Column(
        'change',
        sa.Numeric(10, 5),
        nullable=False
    ),
    # 换手率
    sa.Column(
        'turnover',
        sa.Numeric(10, 2),
        nullable=False
    ),
    extend_existing=True
)


basics = sa.Table(
    'basics',
    metadata,
    # sa.Column(
    #     'id',
    #     sa.Integer,
    #     index=True,
    #     unique=True,
    #     autoincrement=True,
    #     primary_key=True,
    # ),
    sa.Column('sid',
              sa.String(10),
              sa.ForeignKey(equity.c.sid, onupdate='CASCADE', ondelete='CASCADE'),
              nullable=False,
              primary_key=True,
              ),
    sa.Column(
        'name',
        sa.Text,
        nullable=False,
    ),
    sa.Column(
        'market',
        sa.String(20),
        nullable=False
    ),
    sa.Column(
        'ipo_date',
        sa.String(10),
        nullable=False
    ),
    sa.Column(
        'ipo_price',
        sa.String(10),
        nullable=False
    ),
    #
    sa.Column(
        'broker',
        sa.Text,
        nullable=True,
    ),
    sa.Column(
        'district_code',
        sa.Text,
        nullable=True,
    ),
    extend_existing=False,
)


# 除权分红
dividends = sa.Table(
    'dividends',
    metadata,
    # sa.Column(
    #     'id',
    #     sa.Integer,
    #     index=True,
    #     primary_key=True,
    #     autoincrement=True
    # ),
    sa.Column(
        'sid',
        sa.String(10),
        sa.ForeignKey(equity.c.sid, onupdate='CASCADE', ondelete='CASCADE'),
        nullable=False,
        primary_key=True,
    ),
    # 公告日
    sa.Column(
        'declare_date',
        sa.String(10),
        primary_key=True,
    ),
    # 股权登记日下一个交易日就是除权日或除息日
    sa.Column(
        'register_date',
        sa.String(10)
    ),
    # 除权除息日
    sa.Column(
        'ex_date',
        sa.String(10)
    ),
    # 上交所证券的红股上市日为股权除权日的下一个交易日;深交所证券的红股上市日为股权登记日后的第3个交易日
    sa.Column(
        'market_date',
        sa.String(10)
    ),
    # 送股
    sa.Column(
        'bonus',
        sa.Integer,
        default=0,
    ),
    # 转增
    sa.Column(
        'transfer',
        sa.Integer,
        default=0,
    ),
    # 派息
    sa.Column(
        'interest',
        sa.Numeric(10, 5),
        default=0.0
    ),
    # 实施 | 不分配
    sa.Column(
        'progress',
        sa.Text
    ),
    extend_existing=True
    )

# 配股
rights = sa.Table(
    'rights',
    metadata,
    # sa.Column(
    #     'id',
    #     sa.Integer,
    #     index=True,
    #     primary_key=True,
    #     autoincrement=True
    # ),
    sa.Column(
        'sid',
        sa.String(10),
        sa.ForeignKey(equity.c.sid, onupdate='CASCADE', ondelete='CASCADE'),
        nullable=False,
        primary_key=True,
    ),
    # 公告日
    sa.Column(
        'declare_date',
        sa.String(10),
        primary_key=True
    ),
    # 股权登记日
    sa.Column(
        'register_date',
        sa.String(10)
    ),
    # 除权日
    sa.Column(
        'ex_date',
        sa.String(10)
    ),
    # 配股上市日
    sa.Column(
        'market_date',
        sa.String(10)
    ),
    # 配股基数
    sa.Column(
        'benchmark',
        sa.String(30)
    ),
    # 配股方案
    sa.Column(
        'bonus',
        sa.Integer
    ),
    sa.Column(
        'price',
        sa.Numeric(10, 5)
    ),
    extend_existing=True
)

# 股权结构
ownership = sa.Table(
    'ownership',
    metadata,
    # sa.Column(
    #     'id',
    #     sa.Integer,
    #     index=True,
    #     primary_key=True,
    #     autoincrement=True
    # ),
    sa.Column(
        'sid',
        sa.String(10),
        sa.ForeignKey(equity.c.sid, onupdate='CASCADE', ondelete='CASCADE'),
        nullable=False,
        primary_key=True
    ),
    # 变动日与公告日存在 一致的情况（000012， 000002，600109）
    sa.Column(
        'change_date',
        sa.String(10),
        primary_key=True
    ),
    # # 公告日会重复 e.g. 000429 (2020-06-22)
    # sa.Column(
    #     'declare_date',
    #     sa.String(10),
    # ),

    # 总股本
    sa.Column(
        'general',
        sa.String(20),
    ),
    # 流通A股
    sa.Column(
        'float',
        sa.String(20),
        primary_key=True
    ),
    # 限售A股
    sa.Column(
        'strict',
        sa.String(20)
    ),
    extend_existing=True
)

# 市值
m_cap = sa.Table(
    'm_cap',
    metadata,
    # sa.Column(
    #     'id',
    #     sa.Integer,
    #     index=True,
    #     primary_key=True,
    #     autoincrement=True
    # ),
    sa.Column(
        'sid',
        sa.String(6),
        sa.ForeignKey(equity.c.sid, onupdate='CASCADE', ondelete='CASCADE'),
        nullable=False,
        primary_key=True,
    ),
    sa.Column(
        'trade_dt',
        sa.String(10),
        nullable=False,
        primary_key=True
    ),
    # 总市值
    sa.Column(
        'mv',
        sa.Numeric(30, 10),
        nullable=False
    ),
    # 流通市值
    sa.Column(
        'mv_cap',
        sa.Numeric(30, 10),
        nullable=False),
    # 限售市值
    sa.Column(
        'mv_strict',
        sa.Numeric(30, 10),
        nullable=False
    ),
    extend_existing=True
)

# 版本
version_info = sa.Table(
    'version_info',
    metadata,
    sa.Column(
        'id',
        sa.Integer,
        index=True,
        primary_key=True,
        autoincrement=True
    ),
    sa.Column(
        'version',
        sa.Integer,
        unique=True,
        nullable=False,
    ),
    sa.Column(
        'updateTime',
        sa.DateTime,
        server_default=func.now(),
        # onupdate=func.now()
    ),
    # This constraint ensures a single entry in this table
    sa.CheckConstraint('id <= 1'),
    extend_existing=True
)

metadata.create_all(checkfirst=True)
