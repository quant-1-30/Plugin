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

from pipelines.items import TickItem
from crawlers.base import BaseSpider, build_spider_settings


__all__ = ['Benchmark']


class Benchmark(BaseSpider):

    name = 'benchmark'
    table_name = "benchmark"
    
    custom_settings = build_spider_settings(
        log_prefix="benchmark",
        item_pipelines={
            'spider.pipelines.ParquetWriter': 400,
        },
        extra={
            "RETRY_ENABLED": True,
            "RETRY_TIMES": 3,
            "RETRY_HTTP_CODES": [500, 502, 503, 504, 522, 524, 408, 429],
        },
    )

    async def start(self):
        async for req in super().start():
            yield req

    def start_requests(self):
        self.logger.info("Starting index spider...")
        raw_index = os.getenv("INDEX", "")
        index_codes = [code.strip() for code in raw_index.split(',') if '.' in code]
        for index_code in index_codes:
            # '1.000001'
            params = {
                    'secid':  index_code, 
                    'fields1':'f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13',
                    'fields2':'f51,f52,f53,f54,f55,f56,f57,f58',
                    'iscr': 0,
                    'ndays': 5}
            
            start_url = os.getenv("INDEX_URL") + urlencode(params, quote_via=quote)
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
        
        trends = content['data'].get('trends', {})
        if not trends:
            self.logger.warning("No trends found in response")
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

