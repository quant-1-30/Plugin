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


class Fund(BaseSpider):

    name = 'fund'
    table_name = "asset"
    allowed_domains = ['push2.eastmoney.com', 'push2his.eastmoney.com']

    def start_requests(self):
        params = {'fs': 'b:MK0021,b:MK0022,b:MK0023,b:MK0024',
                  'fields': 'f12,f14, f26',
                  'pn': 1,
                  'pz': 10000}
        fund_url = self.routers['assets'] + urlencode(params, quote_via=quote)
        yield scrapy.Request(fund_url, callback=self.parse, 
                             meta={'page': 1, 'params': params}, dont_filter=True)

    def parse(self, response, **kwargs):
        # set response meta
        meta = response.meta
        params = meta['params']
        # content
        content = json.loads(response.text)
        diff = content['data']['diff']
        print("parser", diff)
        if not diff:
            return

        # set loader
        asset = ItemLoader(item=AssetItem())
        for _, obj in diff.items():
            asset.add_value('sid', obj['f12'])
            asset.add_value('name', obj['f14'])
            asset.add_value('first_trading', obj['f26'])

        items = asset.load_item()
        yield items
        
        # next page
        meta['page'] += 1
        params['pn'] = meta['page']
        equity_url = self.routers['assets'] + urlencode(params, quote_via=quote)
        yield scrapy.Request(equity_url, callback=self.parse, 
                             meta={'page': meta['page'], 'params': params}, dont_filter=True)
