# !/usr/bin/env python3
# -*- coding : utf-8 -*-
"""
Created on Tue Mar 12 15:37:47 2019

@author: python
"""
import scrapy, json
from scrapy.loader import ItemLoader
from urllib.parse import urlencode, quote

from spider.tutorial.items import AssetItem
from spider.tutorial.utils import params2url, parse_kline
from spider.tutorial.spiders.base import BaseSpider


class Index(BaseSpider):
    name = 'index'
    allowed_domains = ['push2.eastmoney.com', 'push2his.eastmoney.com']

    # custom_settings = {
    #     'SOME_SETTING': 'some value',
    # }

    def start_requests(self):
        params = {'fs': 'b:MK0010',
                  'fields': 'f12,f14',
                  'pn': 1,
                  'pz': 10000}
        bench_url = self.routers['assets'] + urlencode(params, quote_via=quote)
        yield scrapy.Request(bench_url, callback=self.parse, dont_filter=True)

    def parse(self, response, **kwargs):
        meta = response.meta
        meta['owner'] = 'bench'
        # load json
        content = json.loads(response.text)
        # set loader
        bench = ItemLoader(item=AssetItem())
        meta = response.meta
        bench.add_value('owner', meta['owner'])
        # load assets
        for count, obj in content['data']['diff'].items():
            bench.add_value('sid', obj['f12'])
            bench.add_value('name', obj['f14'])
        # load kline
        items = bench.load_item()
        yield items
        # load kline
        for symbol in items['sid']:
            self.crawl_kline(symbol, meta)
