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

from pipelines.items import TickItem
from crawlers.base import BaseSpider
from utils.operator import async_ops


__all__ = ['Benchmark']


class Benchmark(BaseSpider):

    name = 'benchmark'
    table_name = "benchmark"
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
            'spider.pipelines.ParquetWriter': 400,
            # 'spider.pipelines.JsonlFeed': 500
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
        "LOG_FILE": "logs/benchmark_%s.log" % datetime.now().strftime('%Y%m%d_%H:%M:%S'),
        "LOG_ENABLED": True,
        "LOG_STDOUT": True,  
        "LOG_SHORT_NAMES": True,  
        "LOGSTATS_INTERVAL": 60,  
        "LOGSTATS_DUMP": True,  
        "LOGSTATS_LEVEL": "INFO",  
        "LOGSTATS_FORMAT": "%(asctime)s [%(name)s] %(levelname)s: %(message)s",  
        "LOGSTATS_DATEFORMAT": "%Y-%m-%d %H:%M:%S",  
    }

    def start_requests(self):
        self.logger.info("Starting index spider...")
        indexs = os.getenv("INDEX").split(',')
        for index in indexs:
            # '1.000001'
            params = {
                    'secid':  index, 
                    'fields1':'f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13',
                    'fields2':'f51,f52,f53,f54,f55,f56,f57,f58',
                    'iscr': 0,
                    'ndays': 1}
            
            start_url = os.getenv("INDEX_URL") + urlencode(params, quote_via=quote)
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
        
        trends = content['data'].get('trends', {})
        if not trends:
            self.logger.warning("No diff found in response")
            return
            
        # set loader
        for trend in trends:
            splits = trend.split(',')
            tick = ItemLoader(item=TickItem())
            tick.add_value('sid', content["data"]["code"])
            tick.add_value('tick', splits[0])
            tick.add_value('open', splits[1])
            tick.add_value('close', splits[2])
            tick.add_value('high', splits[3])
            tick.add_value('low', splits[4])
            tick.add_value('volume', splits[5])
            tick.add_value('amount', splits[6])
            item = tick.load_item()
            yield item

