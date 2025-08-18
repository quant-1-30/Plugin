# !/usr/bin/env python3
# -*- coding : utf-8 -*-
"""
Created on Tue Mar 12 15:37:47 2019

@author: python
"""
import json
import gzip

from scrapy.spiders import Spider
from scrapy.exceptions import IgnoreRequest
from tutorial.utils.tools import get_retry_request


class BaseSpider(Spider):
    
    allowed_domains = [
        'push2.eastmoney.com', 
        'push2his.eastmoney.com',
        'example.com',  # Example of an additional domain
    ]
    custom_settings = {
        'CONCURRENT_REQUESTS': 16,  # Example setting: number of concurrent requests
    }
    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super(BaseSpider, cls).from_crawler(crawler, *args, **kwargs)
        routers = crawler.settings.get('META_URLS')
        spider.routers = routers
        return spider
    
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
                return retry_req  # ⚠️ 会在 Spider 方法中判断这个返回是否为 Request
            else:
                self.logger.error(f"[extract_json] 达到最大重试次数，放弃请求: {response.url}")
                raise IgnoreRequest(f"放弃请求: {response.url}")

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
        # 记录错误日志
        self.logger.error(f"[Error] Request failed: {request.url}")
        self.logger.error(f"[Error] Failure type: {failure.type.__name__}")
        self.logger.error(f"[Error] Reason: {repr(failure.value)}")

        # 如果你已经设置了 RetryMiddleware，会自动调用 RetryMiddleware.process_exception
        self.logger.warning(f"[Fail] Giving up on {request.url} after failure.") # 记录/计数/告警 标记失败，用于统计或通知
