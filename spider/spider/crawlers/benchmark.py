# !/usr/bin/env python3
# -*- coding : utf-8 -*-
"""
Created on Tue Mar 12 15:37:47 2019

@author: python
"""
import os
import numpy as np
import scrapy

from datetime import datetime
from urllib.parse import urlencode, quote
from scrapy.loader import ItemLoader

from pipelines.items import KlineItem
from crawlers.base import BaseSpider
from utils.operator import async_ops


__all__ = ['Benchmark']


class Benchmark(BaseSpider):

    name = 'benchmark'
    table_name = "benchmark"
    allowed_domains = ['push2.eastmoney.com', 'finance.sina.com.cn', 'push2his.eastmoney.com', 'push2delay.eastmoney.com']
    handle_httpstatus_list = [301, 302]
    
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
            # 'spider.middlewares.HttpProxyMiddleware': 100,
            'spider.middlewares.UserAgentMiddleware': 200,
            'spider.middlewares.CustomRetryMiddleware': 300,
        },
        "ITEM_PIPELINES": {
            'spider.pipelines.Benchmark': 400,
            'spider.pipelines.AsyncDb': 500,
        },
        "FEEDS": {
            "feeds/benchmark/%(name)s_%(time)s.json": {
                "format": "json",
                "encoding": "utf-8",
                "indent": 4,
            },
        },
        # 日志配置
        "LOG_LEVEL": "INFO",
        "LOG_FORMAT": "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        "LOG_DATEFORMAT": "%Y-%m-%d %H:%M:%S",
        "LOG_FILE": "logs/benchmark_%s.log" % datetime.now().strftime('%Y%m%d_%H:%M:%S'),
        "LOG_ENABLED": True,
        "LOG_STDOUT": True,  # 同时输出到控制台
        "LOG_SHORT_NAMES": True,  # 使用短名称
        "LOGSTATS_INTERVAL": 60,  # 每60秒输出一次统计信息
        "LOGSTATS_DUMP": True,  # 在爬虫关闭时输出统计信息
        "LOGSTATS_LEVEL": "INFO",  # 统计信息的日志级别
        "LOGSTATS_FORMAT": "%(asctime)s [%(name)s] %(levelname)s: %(message)s",  # 统计信息的格式
        "LOGSTATS_DATEFORMAT": "%Y-%m-%d %H:%M:%S",  # 统计信息的时间格式
    }
    bench_data={}

    def preload(self, result): # used to filter
        # import pdb; pdb.set_trace()
        if result:
            r_map = {r[0]: r[1] for r in result}
            self.bench_data = r_map
            self.logger.info(f"Preload Index date {result[0][0]}")

    # async def start(self):
    def start_requests(self):
        # 使用 defer 机制处理异步操作
        bench_sql = """
            WITH ranked_benchmark AS (
                SELECT
                    sid,
                    date,
                    ROW_NUMBER() OVER (PARTITION BY sid ORDER BY date DESC) as rn
                FROM benchmark
            )
            SELECT
                sid,
                date
            FROM ranked_benchmark
            WHERE rn = 1
            ORDER BY sid DESC, date DESC;
        """
        deferred = async_ops.on_query(bench_sql)
        deferred.addCallback(self.preload)
        # deferred.addErrback(self.on_query_error)

        self.logger.info("Starting index spider...")
        indexs = os.getenv("INDEX").split(',')
        for index in indexs:
            params = {'secid':  index, # '1.000001'
                    'fields1':'f1,f2,f3,f4,f5,f6',
                    'fields2':'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61',
                    'klt': '101',
                    'fqt': 1,
                    'beg': 0,
                    'end': 20500101,
                    'lmt': 1000000} 
            start_url = os.getenv("INDEX_URL") + urlencode(params, quote_via=quote)
            self.logger.info(f"Requesting URL: {start_url}")
            print(f"Requesting URL: {start_url}")
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
        
        klines = content['data'].get('klines', {})
        if not klines:
            self.logger.warning("No diff found in response")
            return
            
        # set loader
        for line in klines:
            splits = line.split(',')
            kline = ItemLoader(item=KlineItem())
            kline.add_value('sid', content["data"]["code"])
            kline.add_value('date', splits[0])
            kline.add_value('open', splits[1])
            kline.add_value('close', splits[2])
            kline.add_value('high', splits[3])
            kline.add_value('low', splits[4])
            kline.add_value('volume', splits[5])
            kline.add_value('amount', splits[6])
            item = kline.load_item()
            yield item

