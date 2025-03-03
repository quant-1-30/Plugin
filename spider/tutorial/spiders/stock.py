# !/usr/bin/env python3
# -*- coding : utf-8 -*-
"""
Created on Tue Mar 12 15:37:47 2019

@author: python
"""
import scrapy, json
# from scrapy.spiders import CrawlSpider
from urllib.parse import urlencode, quote
from scrapy.loader import ItemLoader
from spider.tutorial.utils import params2url, parse_kline
from spider.tutorial.items import AssetItem
from spider.tutorial.spiders.base import BaseSpider


class Stock(BaseSpider):
    
    name = 'stock'
    allowed_domains = ['push2.eastmoney.com', 'finance.sina.com.cn', 'push2his.eastmoney.com']
    handle_httpstatus_list = [301, 302]

    def start_requests(self):
        params = {'fs': 'm:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23',
                  'fields': 'f12,f14',
                  'pn': 1,
                  'pz': 50000}
        equity_url = self.routers['assets'] + urlencode(params, quote_via=quote)
        yield scrapy.Request(equity_url, callback=self.parse, dont_filter=True)

    def parse(self, response, **kwargs):
        # set response meta
        meta = response.meta
        meta['owner'] = 'equity'
        content = json.loads(response.text)
        # set loader
        equity = ItemLoader(item=AssetItem())
        equity.add_value('owner', meta['owner'])
        # load assets
        for name, obj in content['data']['diff'].items():
            equity.add_value('sid', obj['f12'])
            equity.add_value('name', obj['f14'])
        items = equity.load_item()
        yield items
        # load kline
        for symbol in items['sid']:
            self.crawl_kline(symbol, meta)
