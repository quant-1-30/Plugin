# !/usr/bin/env python3
# -*- coding : utf-8 -*-
"""
Created on Tue Mar 12 15:37:47 2019

@author: python
"""
import scrapy, json
from scrapy.loader import ItemLoader
from urllib.parse import urlencode, quote

from spider.tutorial.items import DualItem
from spider.tutorial.spiders.base import BaseSpider
from spider.tutorial.utils import params2url, parse_kline


class Dual(BaseSpider):
    name = 'dual'
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
        yield scrapy.Request(dual_url,  callback=self.parse, dont_filter=True)

    def parse(self, response, **kwargs):
        meta = response.meta
        meta['owner'] = 'duals'
        # load json
        content = json.loads(response.text)
        dual = ItemLoader(item=DualItem())
        dual.add_value('owner', meta['owner'])
        # loader assets
        for count, obj in content['data']['diff'].items():
            dual.add_value('sid', obj['f12'])
            dual.add_value('dual', obj['f191'])
            dual.add_value('name', obj['f14'])
        duals = dual.load_item()
        yield duals
        # load kline
        for symbol in duals['sid']:
            self.crawl_kline(symbol, meta)


