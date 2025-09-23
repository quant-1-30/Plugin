# !/usr/bin/env python3
# -*- coding : utf-8 -*-
"""
Created on Tue Mar 12 15:37:47 2019

@author: python
"""
import os
import json
import scrapy
import numpy as np

from urllib.parse import urlencode, quote
from scrapy import  Selector
from scrapy.loader import ItemLoader
# from itemadapter import is_item, ItemAdapter
from itemloaders.processors import TakeFirst, MapCompose, Join

from pipelines.items import *
from crawlers.base import BaseSpider


class Adjustment(BaseSpider):

    name = 'xpath'
    table_name = "adjustment"
    allowed_domains = ['push2.eastmoney.com', 'finance.sina.com.cn', 'push2his.eastmoney.com']
    handle_httpstatus_list = [301, 302]
    
    # override settings
    custom_settings = {
        "AUTOTHROTTLE_ENABLED": True,
        "AUTOTHROTTLE_START_DELAY": np.random.randint(5, 10),
        "AUTOTHROTTLE_MAX_DELAY": np.random.randint(20, 30),
        "AUTOTHROTTLE_TARGET_CONCURRENCY": 1,
        'DOWNLOAD_DELAY': np.random.randint(5, 10),  # Example setting: delay between requests
        'CONCURRENT_REQUESTS': 1,  # Example setting: number of concurrent requests
        # retry
        "RETRY_ENABLED": True,
        "RETRY_TIMES": 3,
        "RETRY_HTTP_CODES": [500, 502, 503, 504, 522, 524, 408, 429],
        "HTTPERROR_ALLOWED_CODES": [301, 302],  # 避免对这些状态报错
        "DOWNLOAD_TIMEOUT": 20,
        # Add more custom settings as needed override settings
        "ITEM_PIPELINES": {
            'spider.pipelines.Adjustment': 400,
            'spider.pipelines.AsyncDb': 500,
        },
        "FEEDS": {
            "feeds/adjustment/%(name)s_%(time)s.json": {
                "format": "json",
                "encoding": "utf-8",
                "indent": 4,
            },
        },
    }

    async def start(self):
        params = {'fs': 'm:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23',
                  'fields': 'f12,f14,f26',
                  'pn': 1,
                  'pz': 50000}
        equity_url = os.getenv("asset_url") + urlencode(params, quote_via=quote)
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

           meta['sid'] = symbol
           asset = 'sh' + symbol if symbol.startswith('6') else 'sz' + symbol
           url_basics = self.routers['aspects'] % asset
           # load basics
           meta["custom_settings"] = {"field":"sina"}
           yield scrapy.Request(url=url_basics, meta=meta.copy(), dont_filter=True, 
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
        target = response.xpath("//div[@class='sec_title']/h3[contains(., '%s')]/a/@href" % '公司资料').getall()
        if target:
            meta["custom_settings"] = {"field":"sina_basics"}
            yield response.follow(url=target[0], meta=meta, dont_filter=True,
                                  callback=self._decode_basics, 
                                  errback=self.errback_httpbin)

    def _decode_basics(self, response, **kwargs):
        # div[@id='con02-0']/
        meta = response.meta
        # set loader
        l_basics = ItemLoader(item=BasicsItem(), response=response)
        # load basics
        l_basics.add_value('owner', 'basics')
        l_basics.add_value('sid', meta['sid'])
        l_basics.add_xpath('name', "//table[@id='comInfo1']/tr[contains(., '公司名称')]/td[@class='ccl']/text()",
                           MapCompose(str.strip))
        l_basics.add_xpath('market', "//table[@id='comInfo1']/tr[contains(., '上市市场')]/td[@class='cc'][1]/text()")
        l_basics.add_xpath('ipo_date', "//table[@id='comInfo1']/tr[contains(., '上市日期')]/td[@class='cc']/a/text()")
        l_basics.add_xpath('ipo_price', "//table[@id='comInfo1']/tr[contains(., '发行价格')]/td[@class='cc'][1]/text()")
        l_basics.add_xpath('broker', "//table[@id='comInfo1']/tr[contains(., '主承销商')]/td[@class='cc']/a/text()")
        l_basics.add_xpath('district_code', "//table[@id='comInfo1']/tr[contains(., '邮政编码')]/td[@class='cc']/text()")
        basics = l_basics.load_item()
        # yield basics and filter stock which has not come to market
        ipo_date = basics.get('ipo_date', None)
        if not ipo_date:
            self.logger.info("Stock %s has not come to market, skip.", meta['sid'])
            return
        
        yield basics

        # load dividends
        target = response.xpath("//div[@class='sec_title']/h3[contains(., '%s')]/a/@href" % '发行分配').getall()[0]
        meta["custom_settings"] = {"field":"sina_adjustment"}
        yield response.follow(url=target, meta=meta, dont_filter=True,
                                callback=self._decode_adjustment, 
                                errback=self.errback_httpbin)

    def _decode_adjustment(self, response, **kwargs):
        meta = response.meta
        # set loader
        l_dividends = ItemLoader(item=Dividend(), response=response)
        # load dividends
        l_dividends.add_value('owner', 'dividends')
        l_dividends.add_value('sid', meta['sid'])
        l_dividends.add_xpath('declare_date', "//table[@id='sharebonus_1']/tbody/tr/td[1]/text()")
        l_dividends.add_xpath('bonus', "//table[@id='sharebonus_1']/tbody/tr/td[2]/text()")
        l_dividends.add_xpath('transfer', "//table[@id='sharebonus_1']/tbody/tr/td[3]/text()")
        l_dividends.add_xpath('interest', "//table[@id='sharebonus_1']/tbody/tr/td[4]/text()")
        l_dividends.add_xpath('progress', "//table[@id='sharebonus_1']/tbody/tr/td[5]/text()")
        l_dividends.add_xpath('ex_date', "//table[@id='sharebonus_1']/tbody/tr/td[6]/text()")
        l_dividends.add_xpath('register_date', "//table[@id='sharebonus_1']/tbody/tr/td[7]/text()")
        l_dividends.add_xpath('market_date', "//table[@id='sharebonus_1']/tbody/tr/td[8]/text()")
        yield l_dividends.load_item()

        # 判断是否存在
        obj = Selector(text=response.text).xpath("//table[@id='sharebonus_2']/tbody/tr[contains(., '暂时没有数据')]/td/text()").getall()
        if not len(obj):
            l_rights = ItemLoader(item=Right(), response=response)
            l_rights.add_value('owner', 'rights')
            l_rights.add_value('sid', meta['sid'])
            l_rights.add_xpath('declare_date', "//table[@id='sharebonus_2']/tbody/tr/td[1]/text()")
            l_rights.add_xpath('bonus', "//table[@id='sharebonus_2']/tbody/tr/td[2]/text()")
            l_rights.add_xpath('price', "//table[@id='sharebonus_2']/tbody/tr/td[3]/text()")
            l_rights.add_xpath('base', "//table[@id='sharebonus_2']/tbody/tr/td[4]/text()")
            l_rights.add_xpath('ex_date', "//table[@id='sharebonus_2']/tbody/tr/td[5]/text()")
            l_rights.add_xpath('register_date', "//table[@id='sharebonus_2']/tbody/tr/td[6]/text()")
            l_rights.add_xpath('market_date', "//table[@id='sharebonus_2']/tbody/tr/td[9]/text()")
            yield l_rights.load_item()
    
       # target = response.xpath("//div[@class='Menu-Con']/tr/td[contains(., '%s')]/a/@href" % '股本结构').getall()[0]
        target = response.xpath("//tr/td[contains(., '%s')]/a/@href" % '股本结构').getall()[0]
        if target:
            meta["custom_settings"] = {"field":"sina_ownership"}
            # load ownership
            yield response.follow(url=target, meta=meta, dont_filter=True,
                                callback=self._decode_ownership, 
                                errback=self.errback_httpbin)

    @staticmethod
    def _decode_ownership(response, **kwargs):
        meta = response.meta
        # set loader
        l_ownership = ItemLoader(item=Ownership(), response=response)
        # load ownership
        l_ownership.add_value('owner', 'ownership')
        l_ownership.add_value('sid', meta['sid'])
        l_ownership.add_xpath('change_date', "//table/tbody/tr[contains(., '变动日期')]/td/text()")
        # l_ownership.add_xpath('declare_date',  "//table/tbody/tr[contains(., '公告日期')]/td/text()")
        l_ownership.add_xpath('general', "//table/tbody/tr[contains(., '总股本')]/td/text()",
                              MapCompose(lambda x: x.split('万股')[0], str.strip))
        l_ownership.add_xpath('float', "//table/tbody/tr[contains(., '流通A股')]/td/text()",
                              MapCompose(lambda x: x.split('万股')[0], str.strip))
        l_ownership.add_xpath('strict', "//table/tbody/tr[contains(., '限售A股')]/td/text()",
                              MapCompose(lambda x: x.split('万股')[0], str.strip))
        yield l_ownership.load_item()

    def errback_httpbin(self, failure):
        # add retry logic
        self.logger.error('Adjustment Request failed: %s', failure)
        request = failure.request
        meta = request.meta
        retry_count = meta.get('retry_count', 0)

        if retry_count < 3:
            meta['retry_count'] = retry_count + 1
            yield scrapy.Request(
                request.url,
                meta=meta,
                callback=request.callback,
                errback=self.errback_httpbin,
                dont_filter=True
            )
        else:
            file_path = os.path.join("record", f'{meta.get("field", "unknown")}.txt')
            with open(file_path, 'a') as f:
                f.write(f"{meta.get('sid', 'unknown')} FAILED\n")
