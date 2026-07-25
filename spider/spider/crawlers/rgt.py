# !/usr/bin/env python3
# -*- coding : utf-8 -*-
"""
Created on Tue Mar 12 15:37:47 2019

@author: python
"""
import os
import scrapy
import numpy as np

from datetime import datetime
from scrapy.loader import ItemLoader
from scrapy import signals
from urllib.parse import urlencode, quote

from pipelines.items import Right
from crawlers.base import BaseSpider
from utils.operator import async_ops

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
        'CONCURRENT_REQUESTS': 1,  # Example setting: number of concurrent requests
        "DOWNLOAD_TIMEOUT": 20,
        # Add more custom settings as needed
        # Middleware settings
        "DOWNLOADER_MIDDLEWARES": {
            # 'spider.middlewares.HttpProxyMiddleware': 100,
            'spider.middlewares.UserAgentMiddleware': 200,
            'spider.middlewares.CustomRetryMiddleware': 300,
        },
        "ITEM_PIPELINES": {
            'spider.pipelines.Rightment': 400,
            'spider.pipelines.AsyncDb': 500,
            'spider.pipelines.JsonlFeed': 600
        },

        # "FEED_EXPORTERS": {
        #     "jsonlines": "spider.export.SafeJsonLinesExporter",
        # },
        # "FEEDS": {
        #     "feeds/rgt/%(name)s_%(time)s.json": {
        #         "format": "json",
        #         "encoding": "utf-8",
        #         "indent": 4,
        #     },
        # },
        "LOG_LEVEL": "INFO",
        "LOG_FORMAT": "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        "LOG_DATEFORMAT": "%Y-%m-%d %H:%M:%S",
        "LOG_FILE": "logs/rgt_%s.log" % datetime.now().strftime('%Y%m%d_%H%M%S'),
        "LOG_ENABLED": True,
        "LOG_STDOUT": True,  
        "LOG_SHORT_NAMES": True,  
        "LOGSTATS_INTERVAL": 60,  
    }
    
    def __init__(self, *args, **kwargs):
        self.rgt_ex_date = {}
        super().__init__(*args, **kwargs)

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        """ bind spider_opened"""
        spider = super().from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.spider_opened, signal=signals.spider_opened)
        return spider

    def spider_opened(self, spider):
        """
            Scrapy wait deferred than start_requests
        """
        self.logger.info("Initializing asset_latest_date from database...")
        rgt_sql = """
            WITH ranked_rgt AS (
                SELECT
                    sid,
                    ex_date,
                    ROW_NUMBER() OVER (PARTITION BY sid ORDER BY ex_date DESC) as rn
                FROM rightment
            )
            SELECT
                sid,
                ex_date
            FROM ranked_rgt
            WHERE rn = 1
            ORDER BY sid DESC, ex_date DESC;
        """
        deferred = async_ops.on_query(rgt_sql)
        deferred.addCallback(self.preload)
        # deferred.addErrback(self.on_query_error)
        return deferred 

    def preload(self, result):
        # retrieve from database
        if result:
            r_map = {r[0]: r[1] for r in result}
            self.rgt_ex_date = r_map

    def start_requests(self):
        params = {'sortColumns': 'EQUITY_RECORD_DATE',
                  'sortTypes': -1,
                  'pageSize': 50,
                  'pageNumber': 1,
                  'reportName': 'RPT_IPO_ALLOTMENT',
                  'columns': 'ALL'}

        start_url = os.getenv('RGT_URL') + urlencode(params, quote_via=quote)
        yield scrapy.Request(start_url, callback=self.parse, 
                             meta={'params': params}, 
                             errback=self.errback_httpbin,
                             dont_filter=True)
        
    async def parse(self, response, **kwargs):
        self.logger.info(f"Response url: {response.url} and status: {response.status}")
        meta = response.meta

        content = self._extract_json_with_retry(response)
        if isinstance(content, scrapy.Request):
            yield content
            return
        
        result = content['result']
        if not result or not result.get('data'):
            self.logger.info(f"No rightment data found for {result}")
            
            if result:
                self.logger.debug(f"Result keys for {list(result.keys())}")
                self.logger.debug(f"Total pages info: {result.get('pages', 'N/A')}")
            else:
                self.logger.warning(f"Empty result")
            return
            
        datas = content['result'].get('data', [])
        if not datas:
            return
    
        data_count = len(datas)
        current_page = meta['params']['pageNumber']
        self.logger.info(f"Found {data_count} rightment records for (page {current_page})")

        for obj in datas:
            # 2023-11-27 00:00:00
            rightment = ItemLoader(item=Right())
            rightment.add_value('sid', obj['SECUCODE'])
            rightment.add_value('report_date', obj['FIRST_NOTICE_DATE'])
            rightment.add_value('register_date', obj['EQUITY_RECORD_DATE'])
            rightment.add_value('ex_date', obj['EX_DIVIDEND_DATE'])
            rightment.add_value('ratio', obj['PLACING_RATIO'])
            rightment.add_value('price', obj['ISSUE_PRICE'])
            item = rightment.load_item()
            self.logger.info(f"Yielding Rightment item: {item}")
            yield item
            
        total_pages = result.get('pages', 1)
        if current_page < total_pages:
            next_params = meta['params'].copy()
            next_params['pageNumber'] = current_page + 1
            next_url = os.getenv('RGT_URL') + urlencode(next_params, quote_via=quote)
            self.logger.info(f"Loading page {next_params['pageNumber']}/{total_pages}")
            yield scrapy.Request(next_url, 
                                callback=self.parse, 
                                meta={'params': next_params}, 
                                dont_filter=True,
                                errback=self.errback_httpbin)
        else:
            self.logger.info(f"Completed all {total_pages} pages for {meta['params'].get('filter', 'N/A')}")
                