# !/usr/bin/env python3
# -*- coding : utf-8 -*-
"""
Created on Tue Mar 12 15:37:47 2019

@author: python
"""
import datetime
import gzip
import numpy as np
import scrapy
import json
from urllib.parse import urlencode, quote
from scrapy.loader import ItemLoader

from tutorial.items import Right
from tutorial.base import BaseSpider

__all__ = ['Rightment']


class Rightment(BaseSpider):

    name = 'rightment'
    table_name = "rightment"
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
            'tutorial.pipelines.Rightment': 400,
            'tutorial.pipelines.AsyncDb': 500,
        },
        # "FEEDS": {
        #     "feeds/rightment/%(name)s_%(time)s.json": {
        #         "format": "json",
        #         "encoding": "utf-8",
        #         "indent": 4,
        #     },
        # },
        # 日志配置
        "LOG_LEVEL": "INFO",
        "LOG_FORMAT": "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        "LOG_DATEFORMAT": "%Y-%m-%d %H:%M:%S",
        "LOG_FILE": "logs/rgt_%s.log" % datetime.datetime.now().strftime('%Y%m%d_%H:%M:%S'),
        "LOG_ENABLED": True,
        "LOG_STDOUT": True,  # 同时输出到控制台
        "LOG_SHORT_NAMES": True,  # 使用短名称
        "LOGSTATS_INTERVAL": 60,  # 每60秒输出一次统计信息
    }

    async def start(self):
        params = {'sortTypes': -1,
                  # pagesize too large will cause data none
                  'pageSize': 50,
                  'pageNumber': 1,
                  'reportName': 'RPT_IPO_ALLOTMENT',
                  'columns': 'ALL'}
        start_url = self.routers['rightment'] + urlencode(params, quote_via=quote)
        yield scrapy.Request(start_url, callback=self.parse, 
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
            self.logger.info(f"Content: {content}")
            
            # Check if the API call was successful
            if not content.get('success', False):
                self.logger.warning(f"API call unsuccessful: {content.get('message', 'Unknown error')}")
                # Retry the request if we haven't exceeded max retries
                return self._retry_request(response)
                
            # Get data from result
            datas = content.get('result', {}).get('data', [])
            if not datas:
                self.logger.info("No data found in response")
                return
    
            for obj in datas:
                # 2023-11-27 00:00:00
                rightment = ItemLoader(item=Right())
                rightment.add_value('sid', obj['SECUCODE'])
                # rightment.add_value('name', obj['SECURITY_NAME_ABBR'])
                # rightment.add_value('declare_date', obj['FIRST_NOTICE_DATE'])
                rightment.add_value('register_date', obj['EQUITY_RECORD_DATE'])
                rightment.add_value('ex_date', obj['EX_DIVIDEND_DATE'])
                # rightment.add_value('market_date', obj['LISTING_DATE'])
                rightment.add_value('ratio', obj['PLACING_RATIO'])
                rightment.add_value('price', obj['ISSUE_PRICE'])
                item = rightment.load_item()
                yield item
            
            # next page
            meta = response.meta
            params = meta['params']
            meta['page'] += 1
            params['pageNumber'] = meta['page']
            next_url = self.routers['rightment'] + urlencode(params, quote_via=quote)
            yield scrapy.Request(next_url, callback=self.parse, 
                                 meta={'page': meta['page'], 'params': params, 'retry_count': 0}, 
                                 errback=self.errback_httpbin,
                                 dont_filter=True)
        except Exception as e:
            self.logger.error(f"Unexpected error in parse: {e}")
            # Retry on unexpected errors
            return self._retry_request(response)

    # def _retry_request(self, response):
    #     """Helper method to retry failed requests"""
    #     meta = response.meta
    #     retry_count = meta.get('retry_count', 0)
    #     max_retries = 3  # Maximum number of retries

    #     if retry_count < max_retries:
    #         self.logger.info(f"Retrying request {response.url} (attempt {retry_count + 1}/{max_retries})")
    #         meta['retry_count'] = retry_count + 1
    #         return scrapy.Request(
    #             response.url,
    #             callback=self.parse,
    #             meta=meta,
    #             errback=self.errback_httpbin,
    #             dont_filter=True
    #         )
    #     else:
    #         self.logger.error(f"Max retries ({max_retries}) exceeded for {response.url}")
    #         return None

    # def errback_httpbin(self, failure):
    #     """Handle request failures"""
    #     request = failure.request
    #     self.logger.error(f"Request failed: {request.url} - {failure.value}")
        
    #     # Retry the request
    #     return self._retry_request(request)
    