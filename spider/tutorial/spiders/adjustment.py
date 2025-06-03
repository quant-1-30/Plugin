# !/usr/bin/env python3
# -*- coding : utf-8 -*-
"""
Created on Tue Mar 12 15:37:47 2019

@author: python
"""
import numpy as np
import scrapy
import json
from urllib.parse import urlencode, quote
from scrapy.loader import ItemLoader

from tutorial.items import Dividend
from tutorial.base import BaseSpider


class Adjustment(BaseSpider):

    name = 'adjustment'
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
        # Add more custom settings as needed
        "ITEM_PIPELINES": {
            'tutorial.pipelines.AsyncDb': 500,
        },
        "FEEDS": {
            "feeds/rightment/%(name)s_%(time)s.json": {
                "format": "json",
                "encoding": "utf-8",
                "indent": 4,
            },
        },
    }

    def start_requests(self): 
        params = {'pageSize': 100,
                  'pageNumber': 1,
                  'reportName': 'RPT_IPO_ALLOTMENT',
                  'columns': 'ALL'}
        equity_url = self.routers['rightment'] + urlencode(params, quote_via=quote)
        yield scrapy.Request(equity_url, callback=self.parse, 
                             meta={'page': 1, 'params': params}, dont_filter=True)

    def parse(self, response, **kwargs):
        # set response meta
        meta = response.meta
        params = meta['params']
        # content
        content = json.loads(response.text)
        datas = content['result']['data']
        if not datas:
            return

        for obj in datas:
            adjustment = ItemLoader(item=Dividend())
            # 2023-11-27 00:00:00
            adjustment.add_value('sid', obj['SECUCODE'])
            adjustment.add_value('name', obj['SECURITY_NAME_ABBR'])
            adjustment.add_value('declare_date', obj['FIRST_NOTICE_DATE'])
            adjustment.add_value('register_date', obj['EQUITY_RECORD_DATE'])
            adjustment.add_value('ex_date', obj['EX_DIVIDEND_DATE'])
            adjustment.add_value('market_date', obj['LISTING_DATE'])
            adjustment.add_value('bonus', obj['PLACING_RATIO'])
            adjustment.add_value('price', obj['ISSUE_PRICE'])
            item = adjustment.load_item()
            self.logger.info(f"Yielding item: {item}")
            yield item
        
        # next page
        meta['page'] += 1
        params['pageNumber'] = meta['page']
        equity_url = self.routers['assets'] + urlencode(params, quote_via=quote)
        yield scrapy.Request(equity_url, callback=self.parse, 
                             meta={'page': meta['page'], 'params': params}, dont_filter=True)
