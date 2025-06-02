# !/usr/bin/env python3
# -*- coding : utf-8 -*-
"""
Created on Tue Mar 12 15:37:47 2019

@author: python
"""
import scrapy
import json
from scrapy.loader import ItemLoader
from urllib.parse import urlencode, quote

from tutorial.items import AssetItem
from tutorial.base import BaseSpider


class Index(BaseSpider):

    name = 'index'
    table_name = "asset"
    allowed_domains = ['push2.eastmoney.com', 'push2his.eastmoney.com']

    def start_requests(self):
        params = {'fs': 'b:MK0010',
                  'fields': 'f12,f14',
                  'pn': 1,
                  'pz': 10000}
        bench_url = self.routers['assets'] + urlencode(params, quote_via=quote)
        yield scrapy.Request(bench_url, callback=self.parse, 
                             meta={'page': 1, 'params': params}, dont_filter=True)

    def parse(self, response, **kwargs):
        meta = response.meta
        params = meta['params']
        # content
        content = json.loads(response.text)
        diff = content['data']['diff']
        print("parser", diff)
        if not diff:
            return

        # set loader
        equity = ItemLoader(item=AssetItem())
        for _, obj in diff.items():
            equity.add_value('sid', obj['f12'])
            equity.add_value('name', obj['f14'])
            equity.add_value('first_trading', obj['f26'])

        items = equity.load_item()
        yield items
        
        # next page
        meta['page'] += 1
        params['pn'] = meta['page']
        equity_url = self.routers['assets'] + urlencode(params, quote_via=quote)
        yield scrapy.Request(equity_url, callback=self.parse, 
                             meta={'page': meta['page'], 'params': params}, dont_filter=True)
