# !/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Mar 12 15:37:47 2019

@author: python
"""
from abc import ABC, abstractmethod
import sqlalchemy as sa, pandas as pd, numpy as np
from functools import partial
from toolz import groupby, valmap


KLINE_COLUMNS_TYPE = {
            'open': np.double,
            'high': np.double,
            'low': np.double,
            'close': np.double,
            'volume': np.int,
            'amount': np.double,
            'pct': np.double
                    }


class Quandle:

    def load_basics(self, owner):
        """
        :param owner: category in (stock ,fund ,bond ,index ,dual)
        :return:
        """

    def load_daily_kline(self, owner):
        """
        :param owner: category in (stock ,fund ,bond ,index ,dual)
        :return:
        """
        table = metadata.tables[owner]
        sqltr = sa.select([
                        table.c.trade_dt,
                        table.c.sid,
                        sa.cast(table.c.open, sa.Numeric(10, 5)).label('open'),
                        sa.cast(table.c.close, sa.Numeric(10, 5)).label('close'),
                        sa.cast(table.c.high, sa.Numeric(10, 5)).label('high'),
                        sa.cast(table.c.low, sa.Numeric(10, 5)).label('low'),
                        sa.cast(table.c.volume, sa.Numeric(20, 0)).label('volume'),
                        sa.cast(table.c.amount, sa.Numeric(20, 5)).label('amount'),
                        sa.cast(table.c.pct, sa.Numeric(15, 2)).label('amplitude'),
                        sa.cast(table.c.pct, sa.Numeric(10, 5)).label('pct'),
                        sa.cast(table.c.pct, sa.Numeric(10, 5)).label('change'),
                        sa.cast(table.c.pct, sa.Numeric(10, 2)).label('turnover')])
        rp = self.engine.execute(sqltr)
        arrays = [[r.sid, r.trade_dt, r.open, r.close, r.high, r.low, r.volume,
                   r.amount, r.amplitude, r.pct, r.change, r.turnover] for r in rp.fetchall()]
        kline = pd.DataFrame(arrays, columns=['sid', 'trade_dt', 'open', 'close', 'high', 'low', 'volume',
                                              'amount', 'amplitude', 'pct', 'change', 'turnover'])
        kline.drop_duplicates(ignore_index=True, inplace=True)
        kline.set_index('sid', inplace=True)
        return kline

    def load_ticker_kline(self, symbol):
        """
            解析bcolz文件
        """
