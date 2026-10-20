# !/usr/bin/env python3
# -*- coding : utf-8 -*-
"""
Created on Tue Mar 12 15:37:47 2019

@author: python
"""
import os
import scrapy

from urllib.parse import urlencode, quote
from scrapy.loader import ItemLoader
from scrapy import signals

from pipelines.items import AssetItem
from crawlers.base import BaseSpider, build_spider_settings
from utils.operator import async_ops
from utils.tools import parse_trading_date_int


__all__ = ['Stock']


class Stock(BaseSpider):

    name = 'stock'
    table_name = "asset"
    
    custom_settings = build_spider_settings(
        log_prefix="stock",
        item_pipelines={
            'spider.pipelines.Asset': 400,
            'spider.pipelines.AsyncDb': 500,
            'spider.pipelines.JsonlFeed': 600,
        },
        extra={
            "RETRY_ENABLED": True,
            "RETRY_TIMES": 3,
            "RETRY_HTTP_CODES": [500, 502, 503, 504, 522, 524, 408, 429],
        },
    )
    def __init__(self, *args, **kwargs):
        self.asset_latest_date = 0
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
        asset_sql = """SELECT max(first_trading) FROM asset"""
        deferred = async_ops.on_query(asset_sql)
        deferred.addCallback(self.preload)
        deferred.addErrback(self.on_watermark_error)
        return deferred  

    def preload(self, result): # used to filter
        if result and result[0][0] is not None:
            self.asset_latest_date = int(result[0][0])
            self.logger.info(f"Preload Newest Asset TradingDay {self.asset_latest_date}")

    async def start(self):
        async for req in super().start():
            yield req

    def start_requests(self):
        self._check_watermark_ready()
        self.logger.info("Starting stock spider...")
        params = {'np': 1,
                  'fltt': 1,
                  'invt': 2,
                  'fs': 'm:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23', # 深市主板/创业板/沪市主板/科创板全量沪深A股
                  'fields': 'f12,f14,f26',
                  'fid':'f26', # nececcery
                  'po': 1,
                  'pn': 1,
                  'pz': 100,
                  'dect': 1}
        start_url = os.getenv("ASSET_URL") + urlencode(params, quote_via=quote)
        self.logger.info(f"Requesting URL: {start_url}")
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
            
        has_newer_record = False
        # set loader
        for obj in diff:
            first_trading = obj.get('f26')
            if parse_trading_date_int(first_trading) > self.asset_latest_date:
                has_newer_record = True
            asset = ItemLoader(item=AssetItem())
            asset.add_value('sid', obj['f12'])
            asset.add_value('name', obj['f14'])
            asset.add_value('first_trading', first_trading)
            item = asset.load_item()
            yield item
            
        # fid=f26 & po=1 按首发上市日降序排列，若当前页已无新于水位的记录，则提前终止翻页
        if not has_newer_record and self.asset_latest_date > 0:
            self.logger.info(f"All records on page {response.meta['page']} are <= {self.asset_latest_date}, stopping pagination early.")
            return

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
