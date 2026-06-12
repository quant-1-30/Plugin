# !/usr/bin/env python3
# -*- coding : utf-8 -*-
"""
Created on Tue Mar 12 15:37:47 2019

@author: python
"""
import os
import numpy as np
import scrapy

from datetime import datetime
from urllib.parse import urlencode, quote
from scrapy.loader import ItemLoader

from pipelines.items import AssetItem
from crawlers.base import BaseSpider
from utils.operator import async_ops


__all__ = ['Stock']


class Stock(BaseSpider):

    name = 'stock'
    table_name = "asset"
    allowed_domains = ['push2.eastmoney.com', 'finance.sina.com.cn', 'push2his.eastmoney.com', 'push2delay.eastmoney.com']
    handle_httpstatus_list = [301, 302]
    
    custom_settings = {
        "AUTOTHROTTLE_ENABLED": True,
        "AUTOTHROTTLE_START_DELAY": np.random.randint(5, 10),
        "AUTOTHROTTLE_MAX_DELAY": np.random.randint(20, 30),
        "AUTOTHROTTLE_TARGET_CONCURRENCY": 1,
        'CONCURRENT_REQUESTS': 1,  # Example setting: number of concurrent requests
        # retry
        "RETRY_ENABLED": True,
        "RETRY_TIMES": 3,
        "RETRY_HTTP_CODES": [500, 502, 503, 504, 522, 524, 408, 429],
        "HTTPERROR_ALLOWED_CODES": [301, 302],  
        "DOWNLOAD_TIMEOUT": 20,
        # Add more custom settings as needed
        # Middleware settings
        "DOWNLOADER_MIDDLEWARES": {
            # 'spider.middlewares.HttpProxyMiddleware': 100,
            'spider.middlewares.UserAgentMiddleware': 200,
            'spider.middlewares.CustomRetryMiddleware': 300,
        },
        "ITEM_PIPELINES": {
            'spider.pipelines.Asset': 400,
            'spider.pipelines.AsyncDb': 500,
            'spider.pipelines.JsonlFeed': 600
        },

        # "FEED_EXPORTERS": {
        #     "jsonlines": "spider.export.SafeJsonLinesExporter",
        # },
        # "FEEDS": {
        #     "feeds/stock/%(name)s_%(time)s.json": {
        #         "format": "json",
        #         "encoding": "utf-8",
        #         "indent": 4,
        #     },
        # },
        "LOG_LEVEL": "INFO",
        "LOG_FORMAT": "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        "LOG_DATEFORMAT": "%Y-%m-%d %H:%M:%S",
        "LOG_FILE": "logs/stock_%s.log" % datetime.now().strftime('%Y%m%d_%H%M%S'),
        "LOG_ENABLED": True,
        "LOG_STDOUT": True,  
        "LOG_SHORT_NAMES": True,  
        "LOGSTATS_INTERVAL": 60,  
        "LOGSTATS_DUMP": True,  
        "LOGSTATS_LEVEL": "INFO",  
        "LOGSTATS_FORMAT": "%(asctime)s [%(name)s] %(levelname)s: %(message)s",  
        "LOGSTATS_DATEFORMAT": "%Y-%m-%d %H:%M:%S",  
    }
    asset_latest_date=0

    def preload(self, result): # used to filter
        if result:
            self.asset_latest_date = int(result[0][0])
            self.logger.info(f"Preload Newest Asset TradingDay {result[0][0]}")

    # async def start(self):
    def start_requests(self):
        adj_sql = """SELECT max(first_trading) FROM asset"""
        deferred = async_ops.on_query(adj_sql)
        deferred.addCallback(self.preload)
        # deferred.addErrback(self.on_query_error)

        self.logger.info("Starting stock spider...")
        params = {'np': 1,
                  'fltt': 1,
                  'invt': 2,
                  'fs': 'm:0+f:8,m:1+f:8',# m:0 上海 / m:1 深圳 / f:8 正常上市
                  'fields': 'f12,f14,f26',
                  'fid':'f26', # nececcery
                  'po': 1,
                  'pn': 1,
                  'pz': 20,
                  'dect': 1} # 10000
        start_url = os.getenv("ASSET_URL") + urlencode(params, quote_via=quote)
        self.logger.info(f"Requesting URL: {start_url}")
        print(f"Requesting URL: {start_url}")
        yield scrapy.Request(start_url, callback=self.parse, 
                             meta={'page': 1, 'params': params, 'retry_times': 0}, 
                             errback=self.errback_httpbin,
                             dont_filter=True)

    async def parse(self, response, **kwargs):
        self.logger.info(f"Response headers: {response.headers} url: {response.url} and status: {response.status}")
        
        content = self._extract_json_with_retry(response)
        if isinstance(content, scrapy.Request):
            yield content
            return
        
        if not content or not content.get('data'):
            self.logger.warning("No data found in response")
            return
        
        diff = content['data'].get('diff', {})
        if not diff:
            self.logger.warning("No diff found in response")
            return
            
        # set loader
        for obj in diff:
            asset = ItemLoader(item=AssetItem())
            asset.add_value('sid', obj['f12'])
            asset.add_value('name', obj['f14'])
            asset.add_value('first_trading', obj['f26'])
            item = asset.load_item()
            yield item
            
        # next page
        meta = response.meta
        meta['page'] += 1
        next_params = meta['params'].copy()
        next_params['pn'] = meta['page']
        next_url = os.getenv("ASSET_URL") + urlencode(next_params, quote_via=quote)
        self.logger.info(f"Requesting next page: {next_url}")

        yield scrapy.Request(next_url, callback=self.parse, 
                             meta={'page': meta['page'], 'params': next_params, 'retry_times': 0}, 
                             errback=self.errback_httpbin,
                             dont_filter=True)
