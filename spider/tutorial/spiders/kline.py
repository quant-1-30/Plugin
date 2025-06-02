# !/usr/bin/env python3
# -*- coding : utf-8 -*-
"""
Created on Tue Mar 12 15:37:47 2019

@author: python
"""
import scrapy
import json
from urllib.parse import urlencode, quote
from scrapy.loader import ItemLoader

from tutorial.items import KlineItem
from tutorial.base import BaseSpider


class Kline(BaseSpider):

    name = 'kline'
    table_name = "tick"
    allowed_domains = ['push2.eastmoney.com', 'finance.sina.com.cn', 'push2his.eastmoney.com']
    handle_httpstatus_list = [301, 302]
    
    # custom_settings = {
    #     'SOME_SETTING': 'some value',
    # }

    # def start_requests(self):  $ deprecated in future version
    async def start(self):
        params = {'fs': 'm:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23',
                  'fields': 'f12,f14,f26',
                  'pn': 1,
                  'pz': 50000}
        equity_url = self.routers['assets'] + urlencode(params, quote_via=quote)
        yield scrapy.Request(equity_url, callback=self.parse, 
                             meta={'page': 1, 'params': params}, dont_filter=True)
        
    def parse(self, response, **kwargs):
        meta = response.meta.copy()
        params = meta['params']
        # handle_httpstatus_all
        meta['dont_redirect'] = True
        meta['dont_retry'] = False
        meta['dont_filter'] = True
        # content
        content = json.loads(response.text)
        diff = content['data']['diff']
        if not diff:
            self.logger.info("No more data, end of pagination.")
            return

        for _, obj in diff.items():
           symbol = obj['f12']

           asset = 'sh' + symbol if symbol.startswith('6') else 'sz' + symbol
           url_kline = self.routers['kline'] % asset
           # meta['sid'] = symbol
           meta["custom_settings"] = {"sid": symbol}
           yield scrapy.Request(url=url_kline, meta=meta.copy(), dont_filter=True, 
                                callback=self._decode, 
                                errback=self.errback_httpbin)
        
        # next stock page
        next_page = meta['page'] + 1
        params['pn'] = next_page
        next_url = self.routers['assets'] + urlencode(params, quote_via=quote)
        yield scrapy.Request(next_url, callback=self.parse, 
                             meta={'page': next_page, 'params': params}, dont_filter=True)

    def _decode(self, response, **kwargs):
        meta = response.meta
        sid = meta['custom_settings']['sid']
        # load json
        content = json.loads(response.text)
        klines = content['data']
        # item loader
        kline = ItemLoader(item=KlineItem())
        if klines and klines['klines']:
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
        yield kline.load_item()
    