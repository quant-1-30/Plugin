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

from tutorial.items import DualItem
from tutorial.base import BaseSpider


class Dual(BaseSpider):

    name = 'dual'
    table_name = "asset"
    allowed_domains = ['push2.eastmoney.com', 'push2his.eastmoney.com']

    # custom_settings = {
    #     'SOME_SETTING': 'some value',
    # }
    def start_requests(self):
        # load dual
        params = {'fs': 'b:DLMK0101',
                  'fields': 'f12,f191,f14',
                  'pn': 1,
                  'pz': 10000}
        # dual_url = Routers['universe'] + urlencode(params, quote_via=quote)
        dual_url = self.routers['assets'] + urlencode(params, quote_via=quote)
        yield scrapy.Request(dual_url,  callback=self.parse, 
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
        asset = ItemLoader(item=DualItem())
        for _, obj in diff.items():
            asset.add_value('sid', obj['f12'])
            asset.add_value('name', obj['f14'])
            asset.add_value('dual', obj['f16'])

        items = asset.load_item()
        yield items
        
        # next page
        meta['page'] += 1
        params['pn'] = meta['page']
        equity_url = self.routers['assets'] + urlencode(params, quote_via=quote)
        yield scrapy.Request(equity_url, callback=self.parse, 
                             meta={'page': meta['page'], 'params': params}, dont_filter=True)
