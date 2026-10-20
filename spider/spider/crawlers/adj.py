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

from pipelines.items import Dividend
from crawlers.base import BaseSpider, build_spider_settings
from utils.tools import quarter_date, get_adjacent_quarter
from utils.operator import async_ops


__all__ = ['Adjustment']


class Adjustment(BaseSpider):

    name = 'adjustment'
    table_name = "adjustment"
    
    custom_settings = build_spider_settings(
        log_prefix="adj",
        item_pipelines={
            'spider.pipelines.Adjustment': 400,
            'spider.pipelines.AsyncDb': 500,
            'spider.pipelines.JsonlFeed': 600,
        },
    )
    
    def __init__(self, *args, **kwargs):
        self.adj_ex_date = {}
        self.adj_known_keys = set()
        super().__init__(*args, **kwargs)

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super().from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.spider_opened, signal=signals.spider_opened)
        return spider

    def spider_opened(self, spider):
        self.logger.info("Initializing adjustment latest ex_date from database...")
        return async_ops.query_latest_ex_dates(
            self.table_name,
            self.preload,
            errback=self.on_watermark_error,
        )

    def preload(self, result):
        self.adj_ex_date, self.adj_known_keys = self._build_ex_date_watermarks(result)

    async def start(self):
        async for req in super().start():
            yield req

    def start_requests(self):
        self._check_watermark_ready()
        base_params = {'sortColumns': 'EX_DIVIDEND_DATE',
                       'sortTypes': -1,
                       'pageSize': 500,
                       'pageNumber': 1,
                       'reportName': 'RPT_SHAREBONUS_DET',
                       'columns': 'ALL'}

        if self.adj_ex_date:
            # 增量模式：按 EX_DIVIDEND_DATE 服务端过滤，覆盖往期年报/中报晚实施除权的分红且无需逐季度轮询
            start_date = get_adjacent_quarter(self.adj_ex_date, offset=0)
            self.logger.info(f"Adjustment incremental EX_DIVIDEND_DATE >= {start_date}")
            params = base_params.copy()
            params['filter'] = f"(EX_DIVIDEND_DATE>='{start_date}')"
            start_url = os.getenv('ADJ_URL') + urlencode(params, quote_via=quote)
            self.logger.info(f"Start url: {start_url}")
            yield scrapy.Request(start_url, callback=self.parse,
                                 meta={'params': params, 'report_date': f">={start_date}"},
                                 errback=self.errback_httpbin,
                                 dont_filter=True)
            return

        # 首次空表引导：按 REPORT_DATE 季度枚举全历史
        start_date = '1990-01-01'
        self.logger.info(f"Adjustment bootstrap Start_date : {start_date}")
        for report_date in quarter_date(start_date):
            self.logger.info(f"Report date: {report_date}")
            params = base_params.copy()
            params['sortColumns'] = 'REPORT_DATE'
            params['filter'] = f"(REPORT_DATE='{report_date}')"
            start_url = os.getenv('ADJ_URL') + urlencode(params, quote_via=quote)
            self.logger.info(f"Start url: {start_url}")
            yield scrapy.Request(start_url, callback=self.parse, 
                                 meta={'params': params, 'report_date': report_date},
                                 errback=self.errback_httpbin,
                                 dont_filter=True)
        
    async def parse(self, response, **kwargs):
        self.logger.info(f"Response url: {response.url} and status: {response.status}")
        meta = response.meta

        content = self._extract_json_with_retry(response)
        if isinstance(content, scrapy.Request):
            yield content
            return
            
        self.logger.debug(f"Adjustment content: {content}")
        result = content.get('result') if content else None
        if not result or not result.get('data'):
            self.logger.info(f"No dividend data found for date (filter: {meta['params'].get('filter', 'N/A')})")
            if result:
                self.logger.debug(f"Result keys for {meta['params'].get('filter', 'N/A')}: {list(result.keys())}")
                self.logger.debug(f"Total pages info: {result.get('pages', 'N/A')}")
            else:
                self.logger.warning(f"Empty result for {meta['params'].get('filter', 'N/A')}")
            return
              
        data_count = len(result['data'])
        report_date = meta.get('report_date', 'unknown date')
        current_page = meta['params']['pageNumber']
        self.logger.info(f"Found {data_count} dividend records for {report_date} (page {current_page})")
        
        for obj in result['data']:
            adjustment = ItemLoader(item=Dividend())
            adjustment.add_value('sid', obj['SECUCODE'])
            adjustment.add_value('report_date', obj['REPORT_DATE'])
            adjustment.add_value('register_date', obj['EQUITY_RECORD_DATE'])
            adjustment.add_value('ex_date', obj['EX_DIVIDEND_DATE'])
            adjustment.add_value('bonus_share', obj['BONUS_RATIO'] if obj.get('BONUS_RATIO') is not None else 0) # 送股
            adjustment.add_value('transfer', obj['IT_RATIO'] if obj.get('IT_RATIO') is not None else 0) # 转股
            adjustment.add_value('bonus', obj['PRETAX_BONUS_RMB'] if obj.get('PRETAX_BONUS_RMB') is not None else 0) # /10
            item = adjustment.load_item()
            self.logger.debug(f"Yielding Adjustment item: {item}")
            yield item

        # check pagenumber
        total_pages = result.get('pages', 1)
        if current_page < total_pages:
            next_params = meta['params'].copy()
            next_params['pageNumber'] = current_page + 1
            next_url = os.getenv('ADJ_URL') + urlencode(next_params, quote_via=quote)
            self.logger.info(f"Loading page {next_params['pageNumber']}/{total_pages} for {meta['params'].get('filter', 'N/A')}")
            yield scrapy.Request(next_url, 
                                 callback=self.parse, 
                                 meta={'params': next_params, 'report_date': report_date}, 
                                 errback=self.errback_httpbin,
                                 dont_filter=True)
        else:
            self.logger.info(f"Completed all {total_pages} pages for {meta['params'].get('filter', 'N/A')}")
