# !/usr/bin/env python3
# -*- coding : utf-8 -*-
"""
Created on Tue Mar 12 15:37:47 2019

@author: python
"""
import scrapy
from scrapy.spiders import CrawlSpider
from datetime import datetime
from spider.tutorial.utils import params2url, parse_kline


class BaseSpider(CrawlSpider):
    
    allowed_domains = [
        'push2.eastmoney.com', 
        'push2his.eastmoney.com',
        'example.com',  # Example of an additional domain
    ]

    custom_settings = {
        'DOWNLOAD_DELAY': 2,  # Example setting: delay between requests
        'CONCURRENT_REQUESTS': 16,  # Example setting: number of concurrent requests
        # 'FEED_URI': 'feeds/%(name)s_%(time)s.json',  # Use parameters in the URI
        # 'FEED_FORMAT': 'json',  # Specify the format (e.g., json, csv, xml)
        # 'FEED_URI_PARAMS': 'spider.tutorial.spiders.base.uri_params',  # Reference to the function
        # 'FEED_EXPORT_ENCODING': 'utf-8',  # Ensure correct encoding
        # Add more custom settings as needed
    }

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super(BaseSpider, cls).from_crawler(crawler, *args, **kwargs)
        routers = crawler.settings.get(
            'META_URLS')
        spider.routers = routers
        return spider
    
    def crawl_kline(self, symbol, meta):
            url_kline = params2url(symbol)
            meta['sid'] = symbol
            yield scrapy.Request(url_kline, meta=meta, callback=parse_kline, dont_filter=True)

# # generate the parameters for the feed URI.
# def uri_params(params, spider):
#     return {
#         'time': datetime.now().strftime('%Y%m%d_%H%M%S'),
#         'name': spider.name,
#     }

