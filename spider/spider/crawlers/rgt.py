# !/usr/bin/env python3
# -*- coding : utf-8 -*-
"""
Created on Tue Mar 12 15:37:47 2019

@author: python
"""
import os
import scrapy

from scrapy.loader import ItemLoader
from scrapy import signals
from urllib.parse import urlencode, quote

from pipelines.items import Right
from crawlers.base import BaseSpider, build_spider_settings
from utils.operator import async_ops
from utils.tools import get_adjacent_quarter

__all__ = ['Rightment']


class Rightment(BaseSpider):

    name = 'rightment'
    table_name = "rightment"
    
    custom_settings = build_spider_settings(
        log_prefix="rgt",
        item_pipelines={
            'spider.pipelines.Rightment': 400,
            'spider.pipelines.AsyncDb': 500,
            'spider.pipelines.JsonlFeed': 600,
        },
    )
    
    def __init__(self, *args, **kwargs):
        self.rgt_ex_date = {}
        self.rgt_known_keys = set()
        super().__init__(*args, **kwargs)

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super().from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.spider_opened, signal=signals.spider_opened)
        return spider

    def spider_opened(self, spider):
        self.logger.info("Initializing rightment latest ex_date from database...")
        return async_ops.query_latest_ex_dates(
            self.table_name,
            self.preload,
            errback=self.on_watermark_error,
        )

    def preload(self, result):
        self.rgt_ex_date, self.rgt_known_keys = self._build_ex_date_watermarks(result)

    async def start(self):
        async for req in super().start():
            yield req

    def start_requests(self):
        self._check_watermark_ready()
        params = {'sortColumns': 'EQUITY_RECORD_DATE',
                  'sortTypes': -1,
                  'pageSize': 500,
                  'pageNumber': 1,
                  'reportName': 'RPT_IPO_ALLOTMENT',
                  'columns': 'ALL'}
        if self.rgt_ex_date:
            start_date = get_adjacent_quarter(self.rgt_ex_date, offset=1)
            params['filter'] = f"(EQUITY_RECORD_DATE>='{start_date}')"

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
        
        result = content.get('result') if content else None
        if not result or not result.get('data'):
            self.logger.info(f"No rightment data found for {result}")
            
            if result:
                self.logger.debug(f"Result keys for {list(result.keys())}")
                self.logger.debug(f"Total pages info: {result.get('pages', 'N/A')}")
            else:
                self.logger.warning(f"Empty result")
            return
            
        datas = result.get('data', [])
        if not datas:
            return
    
        data_count = len(datas)
        current_page = meta['params']['pageNumber']
        self.logger.info(f"Found {data_count} rightment records for (page {current_page})")

        for obj in datas:
            # 2023-11-27 00:00:00
            rightment = ItemLoader(item=Right())
            rightment.add_value('sid', obj.get('SECUCODE', ''))
            rightment.add_value('report_date', obj['FIRST_NOTICE_DATE'])
            rightment.add_value('register_date', obj.get('EQUITY_RECORD_DATE'))
            rightment.add_value('ex_date', obj.get('EX_DIVIDEND_DATE'))
            rightment.add_value('ratio', obj['PLACING_RATIO'] if obj.get('PLACING_RATIO') is not None else 0)
            rightment.add_value('price', obj['ISSUE_PRICE'] if obj.get('ISSUE_PRICE') is not None else 0)
            item = rightment.load_item()
            self.logger.debug(f"Yielding Rightment item: {item}")
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
                