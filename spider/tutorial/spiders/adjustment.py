# !/usr/bin/env python3
# -*- coding : utf-8 -*-
"""
Created on Tue Mar 12 15:37:47 2019

@author: python
"""
from datetime import datetime
import numpy as np
import gzip
import scrapy
import json
from urllib.parse import urlencode, quote
from scrapy.loader import ItemLoader

from tutorial.items import Dividend
from tutorial.base import BaseSpider

__all__ = ['Adjustment']


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
        'DOWNLOAD_DELAY': np.random.randint(10, 20),  # Example setting: delay between requests
        'CONCURRENT_REQUESTS': 1,  # Example setting: number of concurrent requests
        # retry
        "RETRY_ENABLED": True,
        "RETRY_TIMES": 5,
        "RETRY_HTTP_CODES": [500, 502, 503, 504, 522, 524, 408, 429],
        "HTTPERROR_ALLOWED_CODES": [301, 302],  # 避免对这些状态报错
        "DOWNLOAD_TIMEOUT": 20,
        # Add more custom settings as needed
        # Middleware settings
        "DOWNLOADER_MIDDLEWARES": {
            'tutorial.middlewares.UserAgentMiddleware': 400,
        },
        "ITEM_PIPELINES": {
            'tutorial.pipelines.Adjustment': 400,
            'tutorial.pipelines.AsyncDb': 500,
        },
        # "FEEDS": {
        #     "feeds/rightment/%(name)s_%(time)s.json": {
        #         "format": "json",
        #         "encoding": "utf-8",
        #         "indent": 4,
        #     },
        # },
        "LOG_LEVEL": "INFO",
        "LOG_FORMAT": "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        "LOG_DATEFORMAT": "%Y-%m-%d %H:%M:%S",
        "LOG_FILE": "logs/adj_%s.log" % datetime.now().strftime('%Y%m%d_%H:%M:%S'),
        "LOG_ENABLED": True,
        "LOG_STDOUT": True,  # 同时输出到控制台
        "LOG_SHORT_NAMES": True,  # 使用短名称
        "LOGSTATS_INTERVAL": 60,  # 每60秒输出一次统计信息
    }

    async def start(self):
        params = {'fs': 'm:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23',
                  'fields': 'f12,f14,f26',
                  'pn': 1,
                  'pz': 50}
        start_url = self.routers['assets'] + urlencode(params, quote_via=quote)
        yield scrapy.Request(start_url, callback=self.parse, 
                             meta={'page': 1, 'params': params, 'retry_count': 0}, 
                             errback=self.errback_httpbin,
                             dont_filter=True)
        
    def parse(self, response, **kwargs):
        self.logger.info(f"Response headers: {response.headers} url: {response.url} and status: {response.status}")
        meta = response.meta
        meta['retry_count'] = 0
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
            
            # setup adjustment params
            _params = {'sortColumns': 'REPORT_DATE',
                      'sortTypes': -1,
                      'pageSize': 100,
                      'pageNumber': 1,
                      'reportName': 'RPT_SHAREBONUS_DET',
                      'columns': 'ALL'}

            for _, obj in diff.items():
                symbol = obj['f12']
                _params["filter"] = f'(SECURITY_CODE="{symbol}")' 
                # start_url = self.routers['adjustment'] + urlencode(_params, quote_via=quote, safe='()')
                start_url = self.routers['adjustment'] + urlencode(_params, quote_via=quote)
                self.logger.info(f"Start url: {start_url}")
                yield scrapy.Request(url=start_url, meta=meta.copy(), dont_filter=True, 
                                     callback=self._decode, 
                                     errback=self.errback_httpbin)
            # next stock page
            params = meta['params']
            meta['page'] += 1
            params['pn'] = meta['page']
            next_url = self.routers['assets'] + urlencode(params, quote_via=quote)
            yield scrapy.Request(next_url, callback=self.parse, 
                                 meta={'page': meta['page'], 'params': params}, dont_filter=True)
        except Exception as e:
            self.logger.error(f"Unexpected error in parse: {e}")
            # Retry on unexpected errors
            yield self._retry_request(response)

    def _decode(self, response, **kwargs):
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
            self.logger.info(f"Adjustment content: {content}")
            datas = content['result'].get('data', [])
            if not datas:
                return 
    
            for obj in datas:
                adjustment = ItemLoader(item=Dividend())
                adjustment.add_value('sid', obj['SECUCODE'])
                adjustment.add_value('report_date', obj['REPORT_DATE'])
                adjustment.add_value('register_date', obj['EQUITY_RECORD_DATE'])
                adjustment.add_value('ex_date', obj['EX_DIVIDEND_DATE'])
                adjustment.add_value('bonus_share', obj['BONUS_RATIO']) # 送股
                adjustment.add_value('transfer', obj['IT_RATIO']) # 转股
                adjustment.add_value('bonus', obj['PRETAX_BONUS_RMB']) # /10
                item = adjustment.load_item()
                self.logger.info(f"Yielding Adjustment item: {item}")
                yield item
            
        except Exception as e:
            self.logger.error(f"Unexpected error in parse: {e}")
            yield self._retry_request(response)
