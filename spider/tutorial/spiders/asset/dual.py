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

from tutorial.items import DualItem
from tutorial.base import BaseSpider

__all__ = ['Dual']


class Dual(BaseSpider):

    name = 'dual'
    table_name = "asset"
    allowed_domains = ['push2.eastmoney.com', 'push2his.eastmoney.com']

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
            'tutorial.middlewares.UserAgentMiddleware': 400,
        },
        "ITEM_PIPELINES": {
            'tutorial.pipelines.Asset': 400,
            'tutorial.pipelines.AsyncDb': 500,
        },
        "FEEDS": {
            "feeds/dual/%(name)s_%(time)s.json": {
                "format": "json",
                "encoding": "utf-8",
                "indent": 4,
            },
        },
        # 日志配置
        "LOG_LEVEL": "INFO",
        "LOG_FORMAT": "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        "LOG_DATEFORMAT": "%Y-%m-%d %H:%M:%S",
        "LOG_FILE": "logs/dual_%s.log" % datetime.now().strftime('%Y%m%d_%H:%M:%S'),
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
        # load dual
        params = {'fs': 'b:DLMK0101',
                  'fields': 'f12,f191,f14',
                  'pn': 1,
                  'pz': 100}
        # dual_url = Routers['universe'] + urlencode(params, quote_via=quote)
        start_url = self.routers['assets'] + urlencode(params, quote_via=quote)
        yield scrapy.Request(start_url,  callback=self.parse, 
                             meta={'page': 1, 'params': params, 'retry_count': 0}, 
                             errback=self.errback_httpbin,
                             dont_filter=True)

    def parse(self, response, **kwargs):
        self.logger.info(f"Response headers: {response.headers} url: {response.url} and status: {response.status}")
        try:
            # 检查响应是否被压缩
            body = (
                gzip.decompress(response.body)
                if response.headers.get('Content-Encoding') == b'gzip'
                else response.body
            )
            # content
            content = json.loads(body)
            diff = content['data'].get('diff', {})
            if not diff:
                return
            
            for _, obj in diff.items():
                dual = ItemLoader(item=DualItem())
                dual.add_value('sid', obj['f12'])
                dual.add_value('name', obj['f14'])
                dual.add_value('dual', obj['f16'])

                item = dual.load_item()
                yield item
            
            # next page
            # set response meta
            meta = response.meta
            params = meta['params']
            meta['page'] += 1
            params['pn'] = meta['page']
            next_url = self.routers['assets'] + urlencode(params, quote_via=quote)
            yield scrapy.Request(next_url, callback=self.parse, 
                                 meta={'page': meta['page'], 'params': params, 'retry_count': 0}, 
                                 errback=self.errback_httpbin,
                                 dont_filter=True)
        except Exception as e:
            self.logger.error(f"Unexpected error in parse: {e}")
            return self._retry_request(response)
