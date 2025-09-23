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
from urllib.parse import urlencode, quote
from scrapy.loader import ItemLoader

from pipelines.items import Dividend
from crawlers.base import BaseSpider
from utils.tools import quarter_date
from utils.operator import async_ops


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
        'DOWNLOAD_DELAY': np.random.randint(5, 10),  # Example setting: delay between requests
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
            'spider.pipelines.Adjustment': 400,
            'spider.pipelines.AsyncDb': 500,
        },
        "FEEDS": {
            "feeds/adj/%(name)s_%(time)s.json": {
                "format": "json",
                "encoding": "utf-8",
                "indent": 4,
            },
        },
        "LOG_LEVEL": "INFO",
        "LOG_FORMAT": "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        "LOG_DATEFORMAT": "%Y-%m-%d %H:%M:%S",
        "LOG_FILE": "logs/adj_%s.log" % datetime.now().strftime('%Y%m%d_%H:%M:%S'),
        "LOG_ENABLED": True,
        "LOG_STDOUT": True,  # 同时输出到控制台
        "LOG_SHORT_NAMES": True,  # 使用短名称
        "LOGSTATS_INTERVAL": 60,  # 每60秒输出一次统计信息
    }

    adj_ex_date = {}

    def preload(self, results):
        # retrieve from database
        r_map = {r[0]: r[1] for r in results}
        self.adj_ex_date = r_map
        # import pdb; pdb.set_trace()

    # async def start(self):
    def start_requests(self):
        # 使用 defer 机制处理异步操作
        adj_sql = """
            WITH ranked_adj AS (
                SELECT
                    sid,
                    ex_date,
                    ROW_NUMBER() OVER (PARTITION BY sid ORDER BY ex_date DESC) as rn
                FROM adjustment
            )
            SELECT
                sid,
                ex_date
            FROM ranked_adj
            WHERE rn = 1
            ORDER BY sid DESC, ex_date DESC;
        """
        deferred = async_ops.on_query(adj_sql)
        deferred.addCallback(self.preload)
        # deferred.addErrback(self.on_query_error)

        start_date = os.getenv('ADJ_UPDT', '1990-01-01') 
        base_params = {'sortColumns': 'REPORT_DATE',
                       'sortTypes': -1,
                       'pageSize': 50,
                       'pageNumber': 1,
                       'reportName': 'RPT_SHAREBONUS_DET',
                       'columns': 'ALL'}

        for report_date in quarter_date(start_date):
            self.logger.info(f"Report date: {report_date}")
            params = base_params.copy()
            params['filter'] = f"(REPORT_DATE='{report_date}')"
            # setup adjustment params
            start_url = os.getenv('ADJ_URL') + urlencode(params, quote_via=quote)
            self.logger.info(f"Start url: {start_url}")
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
            
        self.logger.info(f"Adjustment content: {content}")
        result = content['result']
        if not result or not result.get('data'):
            self.logger.info(f"No dividend data found for date (filter: {meta['params']['filter']})")
            if result:
                self.logger.debug(f"Result keys for {meta['params']['filter']}: {list(result.keys())}")
                self.logger.debug(f"Total pages info: {result.get('pages', 'N/A')}")
            else:
                self.logger.warning(f"Empty result for {meta['params']['filter']}")
            return
              
        # 记录找到的数据数量
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
            adjustment.add_value('bonus_share', obj['BONUS_RATIO']) # 送股
            adjustment.add_value('transfer', obj['IT_RATIO']) # 转股
            adjustment.add_value('bonus', obj['PRETAX_BONUS_RMB']) # /10
            item = adjustment.load_item()
            self.logger.info(f"Yielding Adjustment item: {item}")
            yield item

        # 检查分页信息
        total_pages = result.get('pages', 1)
        if current_page <= total_pages:
            # 为下一页创建新的参数副本
            next_params = meta['params'].copy()
            next_params['pageNumber'] = current_page + 1
            next_url = os.getenv('ADJ_URL') + urlencode(next_params, quote_via=quote)
            self.logger.info(f"Loading page {next_params['pageNumber']}/{total_pages} for {meta['params']['filter']}")
            yield scrapy.Request(next_url, 
                                 callback=self.parse, 
                                 meta={'params': next_params}, 
                                 dont_filter=True)
        else:
            self.logger.info(f"Completed all {total_pages} pages for {meta['params']['filter']}")
