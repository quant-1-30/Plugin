# !/usr/bin/env python3
# -*- coding : utf-8 -*-
"""
Created on Tue Mar 12 15:37:47 2019

@author: python
"""
import json
import gzip
from datetime import datetime

import scrapy
from scrapy.spiders import Spider
from scrapy.exceptions import IgnoreRequest, CloseSpider
from utils.tools import get_retry_request
from utils.operator import async_ops

COMMON_THROTTLE_SETTINGS = {
    "AUTOTHROTTLE_ENABLED": True,
    "AUTOTHROTTLE_START_DELAY": 1,
    "AUTOTHROTTLE_MAX_DELAY": 5,
    "AUTOTHROTTLE_TARGET_CONCURRENCY": 4,
    "CONCURRENT_REQUESTS": 4,
    "DOWNLOAD_TIMEOUT": 15,
}


def build_spider_settings(log_prefix: str, item_pipelines: dict, extra: dict = None) -> dict:
    """构建各爬虫统一 custom_settings，消除中间件与日志配置重复。"""
    settings = {
        **COMMON_THROTTLE_SETTINGS,
        "DOWNLOADER_MIDDLEWARES": {
            "spider.middlewares.UserAgentMiddleware": 200,
            "spider.middlewares.CustomRetryMiddleware": 300,
        },
        "ITEM_PIPELINES": item_pipelines,
        "LOG_LEVEL": "INFO",
        "LOG_FORMAT": "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        "LOG_DATEFORMAT": "%Y-%m-%d %H:%M:%S",
        "LOG_FILE": f"logs/{log_prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
        "LOG_ENABLED": True,
        "LOG_STDOUT": True,
        "LOG_SHORT_NAMES": True,
        "LOGSTATS_INTERVAL": 60,
    }
    if extra:
        settings.update(extra)
    return settings


class BaseSpider(Spider):
    
    allowed_domains = [
        'push2.eastmoney.com', 
        'push2his.eastmoney.com',
        'push2delay.eastmoney.com',
        'datacenter-web.eastmoney.com',
        'finance.sina.com.cn',
    ]
    custom_settings = {
        **COMMON_THROTTLE_SETTINGS,
    }

    async def start(self):
        """Scrapy 2.13+ 异步入口，委托给 start_requests() 以消除弃用警告并保持向后兼容。"""
        for request in self.start_requests():
            yield request

    def on_watermark_error(self, failure):
        """数据库水位查询失败回调：标记失败并通知引擎以 watermark_unavailable 原因关闭爬虫。"""
        self._watermark_failed = True
        self.logger.critical(f"[{self.name}] Failed to load watermark from database: {failure.value}")
        if hasattr(self, "crawler") and getattr(self.crawler, "engine", None) is not None:
            self.crawler.engine.close_spider(self, "watermark_unavailable")

    def _check_watermark_ready(self):
        """在发起请求前校验水位是否加载成功，若失败则通知引擎关闭并拒绝产生请求。"""
        if getattr(self, "_watermark_failed", False):
            if hasattr(self, "crawler") and getattr(self.crawler, "engine", None) is not None:
                self.crawler.engine.close_spider(self, "watermark_unavailable")
            raise CloseSpider("watermark_unavailable")

    @staticmethod
    def _build_ex_date_watermarks(result):
        """将数据库 (sid, ex_date) 查询结果聚合为 (最大除权日字典, 已知记录集合)。"""
        ex_map = {}
        known = set()
        if result:
            for sid, ex_date in result:
                if ex_date is not None:
                    known.add((sid, ex_date))
                    if ex_date > ex_map.get(sid, 0):
                        ex_map[sid] = ex_date
        return ex_map, known
    
    def _extract_json_with_retry(self, response):
        # parse failure also need to retry --- return request
        try:
            body = (
                gzip.decompress(response.body)
                if response.headers.get('Content-Encoding') == b'gzip'
                else response.body
            )
            return json.loads(body)
        except Exception as e:
            self.logger.warning(f"[extract_json] JSON解析失败 尝试重试: {e} | URL: {response.url}")
            retry_req = get_retry_request(
                request=response.request,
                reason=f"extract_json_failed: {e}",
                spider=self
            )
            if retry_req:
                return retry_req  # Spider Request
            else:
                self.logger.error(f"[extract_json]: {response.url}")
                raise IgnoreRequest(f"Ingore: {response.url}")

    def errback_httpbin(self, failure):
        """
        errback callback for failed requests.

        This gets triggered when requests raise exceptions such as:
        - TimeoutError
        - DNSLookupError
        - ConnectionRefusedError
        - etc.
        """
        request = failure.request
        
        self.logger.error(f"[Error] Request failed: {request.url}")
        self.logger.error(f"[Error] Failure type: {failure.type.__name__}")
        self.logger.error(f"[Error] Reason: {repr(failure.value)}")

        # RetryMiddleware ---> RetryMiddleware.process_exception
        self.logger.warning(f"[Fail] Giving up on {request.url} after failure.") 
