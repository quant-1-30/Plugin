# !/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Mar 12 15:37:47 2019

@author: python
"""
import re
import json
from scrapy.loader import ItemLoader
from urllib.parse import urlencode, quote
from .items import KlineItem
from .settings import META_URLS, Params


def params2url(sid, dual=False):
    if dual:
        prefix = '116.' + sid
    else:
        pattern = '(^6|5|11|000)[0-9]{4,5}$'
        match = re.match(pattern, sid)
        prefix = '1.' + sid if match else '0.' + sid
    # update sid
    p = Params.copy()
    p.update({'secid': prefix})
    url = META_URLS['kline'] + urlencode(p, quote_via=quote)
    return url


def parse_kline(response, **kwargs):
    meta = response.meta
    sid = meta['sid']
    owner = meta['owner']
    # load json
    content = json.loads(response.text)
    klines = content['data']
    # item loader
    kline = ItemLoader(item=KlineItem())
    if klines and klines['klines']:
        kline.add_value('owner', '%s_price' % owner)
        for obj in klines['klines']:
            items = obj.split(',')
            kline.add_value('trade_dt', items[0])
            kline.add_value('open', items[1])
            kline.add_value('close', items[2])
            kline.add_value('high', items[3])
            kline.add_value('low', items[4])
            kline.add_value('volume', items[5])
            kline.add_value('amount', items[6])
            kline.add_value('amplitude', items[7])
            kline.add_value('pct', items[8])
            kline.add_value('change', items[9])
            kline.add_value('turnover', items[10])
            kline.add_value('sid', sid)
        kline.add_value('owner', owner)
    yield kline.load_item()
