# !/usr/bin/env python3
# -*- coding : utf-8 -*-
"""
Created on Tue Mar 12 15:37:47 2019

@author: python
"""
import scrapy
import json
import gzip
import numpy as np

from datetime import datetime
from urllib.parse import urlencode, quote
from scrapy.loader import ItemLoader

from pipelines.items import AssetItem
from crawlers.base import BaseSpider

__all__ = ['Stock']


class Stock(BaseSpider):

    name = 'stock'
    table_name = "asset"
    allowed_domains = ['push2.eastmoney.com', 'finance.sina.com.cn', 'push2his.eastmoney.com']
    handle_httpstatus_list = [301, 302]
    
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
        # Middleware settings
        "DOWNLOADER_MIDDLEWARES": {
            'tutorial.middlewares.HttpProxyMiddleware': 100,
            'tutorial.middlewares.UserAgentMiddleware': 200,
            'tutorial.middlewares.CustomRetryMiddleware': 300,
        },
        "ITEM_PIPELINES": {
            'tutorial.pipelines.Asset': 400,
            'tutorial.pipelines.AsyncDb': 500,
        },
        # "FEEDS": {
        #     "feeds/stock/%(name)s_%(time)s.json": {
        #         "format": "json",
        #         "encoding": "utf-8",
        #         "indent": 4,
        #     },
        # },
        # 日志配置
        "LOG_LEVEL": "INFO",
        "LOG_FORMAT": "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        "LOG_DATEFORMAT": "%Y-%m-%d %H:%M:%S",
        "LOG_FILE": "logs/stock_%s.log" % datetime.now().strftime('%Y%m%d_%H:%M:%S'),
        "LOG_ENABLED": True,
        "LOG_STDOUT": True,  # 同时输出到控制台
        "LOG_SHORT_NAMES": True,  # 使用短名称
        "LOGSTATS_INTERVAL": 60,  # 每60秒输出一次统计信息
        "LOGSTATS_DUMP": True,  # 在爬虫关闭时输出统计信息
        "LOGSTATS_LEVEL": "INFO",  # 统计信息的日志级别
        "LOGSTATS_FORMAT": "%(asctime)s [%(name)s] %(levelname)s: %(message)s",  # 统计信息的格式
        "LOGSTATS_DATEFORMAT": "%Y-%m-%d %H:%M:%S",  # 统计信息的时间格式
    }

    async def start(self):
        self.logger.info("Starting stock spider...")
        params = {'fs': 'm:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23',
                  'fields': 'f12,f14,f26',
                  'pn': 1,
                  'pz': 50} # 10000
        start_url = self.routers['assets'] + urlencode(params, quote_via=quote)
        self.logger.info(f"Requesting URL: {start_url}")
        yield scrapy.Request(start_url, callback=self.parse, 
                             meta={'page': 1, 'params': params, 'retry_times': 0}, 
                             errback=self.errback_httpbin,
                             dont_filter=True)

    def parse(self, response, **kwargs):
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
        for _, obj in diff.items():
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
        next_url = self.routers['assets'] + urlencode(next_params, quote_via=quote)
        self.logger.info(f"Requesting next page: {next_url}")

        yield scrapy.Request(next_url, callback=self.parse, 
                             meta={'page': meta['page'], 'params': next_params, 'retry_times': 0}, 
                             errback=self.errback_httpbin,
                             dont_filter=True)
