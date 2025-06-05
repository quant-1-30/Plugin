# !/usr/bin/env python3
# -*- coding : utf-8 -*-
"""
Created on Tue Mar 12 15:37:47 2019

@author: python
"""
import numpy as np
import gzip
import scrapy
import json
from scrapy.loader import ItemLoader
from urllib.parse import urlencode, quote
from datetime import datetime

from tutorial.items import BondItem
from tutorial.base import BaseSpider

__all__ = ['Bond']


class Bond(BaseSpider):
    """
        回售最后2年70%, 赎回130%  type=KZZ_HSSH
    """
    name = 'bond'
    allowed_domains = ['dcfm.eastmoney.com', 'push2his.eastmoney.com']

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
        "FEEDS": {
            "feeds/rightment/%(name)s_%(time)s.json": {
                "format": "json",
                "encoding": "utf-8",
                "indent": 4,
            },
        },
        # 日志配置
        "LOG_LEVEL": "INFO",
        "LOG_FORMAT": "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        "LOG_DATEFORMAT": "%Y-%m-%d %H:%M:%S",
        "LOG_FILE": "logs/bond_%s.log" % datetime.now().strftime('%Y%m%d_%H:%M:%S'),
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
        params = {'type': 'KZZ_MX',
                  'token': '894050c76af8597a853f5b408b759f5d'}
        start_url = self.routers['bond'] + urlencode(params, quote_via=quote)
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
        
        try:
            diff = content['data'].get('diff', {})
            if not diff:
                return
    
            for _, obj in diff.items():
                bond = ItemLoader(item=BondItem())
                bond.add_value('sid', obj['f12'])
                bond.add_value('name', obj['f14'])
                bond.add_value('swap_code', obj['f16'])
                bond.add_value('swap_price', obj['f18'])
                bond.add_value('swap_sdate', obj['f20'])
                bond.add_value('swap_edate', obj['f22'])
                item = bond.load_item()
                yield item
            
            # next page
            meta = response.meta
            params = meta['params']
            meta['page'] += 1
            params['pn'] = meta['page']
            next_url = self.routers['assets'] + urlencode(params, quote_via=quote)
            yield scrapy.Request(next_url, callback=self.parse, 
                                 meta={'page': meta['page'], 'params': params, 'retry_times': 0}, 
                                 errback=self.errback_httpbin,
                                 dont_filter=True)
        except Exception as e:
            self.logger.error(f"解析响应失败: {e}, url: {response.url}")
