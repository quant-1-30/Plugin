# !/usr/bin/env python3
# -*- coding : utf-8 -*-
"""
Created on Tue Mar 12 15:37:47 2019

@author: python
"""
import scrapy, json
from scrapy.loader import ItemLoader
from urllib.parse import urlencode, quote
# from . import Routers, params_url, parse_kline
from spider.tutorial.items import AssetItem
from spider.tutorial.utils import params2url, parse_kline
from spider.tutorial.spiders.base import BaseSpider


class Fund(BaseSpider):

    name = 'fund'
    allowed_domains = ['push2.eastmoney.com', 'push2his.eastmoney.com']

    def start_requests(self):
        params = {'fs': 'b:MK0021,b:MK0022,b:MK0023,b:MK0024',
                  'fields': 'f12,f14',
                  'pn': 1,
                  'pz': 10000}
        fund_url = self.routers['assets'] + urlencode(params, quote_via=quote)
        yield scrapy.Request(fund_url, callback=self.parse, dont_filter=True)

    def parse(self, response, **kwargs):
        meta = response.meta
        meta['owner'] = 'fund'
        # load json
        content = json.loads(response.text)
        # loader
        fund = ItemLoader(item=AssetItem())
        # fund.add_value('owner', 'fund')
        fund.add_value('owner', meta['owner'])
        # load assets
        for count, obj in content['data']['diff'].items():
            fund.add_value('sid', obj['f12'])
            fund.add_value('name', obj['f14'])
        items = fund.load_item()
        yield items
        # load kline
        for symbol in items['sid']:
            self.crawl_kline(symbol, meta)
