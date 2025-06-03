# !/usr/bin/env python3
# -*- coding : utf-8 -*-
"""
Created on Tue Mar 12 15:37:47 2019

@author: python
"""
import time
import scrapy
from scrapy.spiders import Spider


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

    def _retry_request(self, response):
        """Helper method to retry failed requests"""
        meta = response.meta
        retry_count = meta.get('retry_count', 0)
        max_retries = 3  # Maximum number of retries

        if retry_count < max_retries:
            self.logger.info(f"Retrying request {response.url} (attempt {retry_count + 1}/{max_retries})")
            meta['retry_count'] = retry_count + 1
            time.sleep(2 ** retry_count)
            return scrapy.Request(
                response.url,
                callback=self.parse,
                meta=meta,
                errback=self.errback_httpbin,
                dont_filter=True
            )
        else:
            self.logger.error(f"Max retries ({max_retries}) exceeded for {response.url}")
            return None

    def errback_httpbin(self, failure):
        """Handle request failures"""
        request = failure.request
        self.logger.error(f"Request failed: {request.url} - {failure.value}")
        
        # Retry the request
        return self._retry_request(request)
    