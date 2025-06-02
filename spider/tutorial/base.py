# !/usr/bin/env python3
# -*- coding : utf-8 -*-
"""
Created on Tue Mar 12 15:37:47 2019

@author: python
"""
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
