# !/usr/bin/env python3
# -*- coding : utf-8 -*-
"""
Created on Tue Mar 12 15:37:47 2019

@author: python
"""
from collections.abc import Iterable
import scrapy
import json
import gzip
from urllib.parse import urlencode, quote
from scrapy.loader import ItemLoader

from tutorial.items import AssetItem
from tutorial.base import BaseSpider


class Stock(BaseSpider):

    name = 'stock'
    table_name = "asset"
    allowed_domains = ['push2.eastmoney.com', 'finance.sina.com.cn', 'push2his.eastmoney.com']
    handle_httpstatus_list = [301, 302]
    
    custom_settings = {
        'ITEM_PIPELINES': {
            'tutorial.pipelines.Asset': 300,
            'tutorial.pipelines.AsyncDb': 400,
        }
    }

    async def start(self):
        self.logger.info("Starting stock spider...")
        params = {'fs': 'm:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23',
                  'fields': 'f12,f14,f26',
                  'pn': 1,
                  'pz': 50000}
        equity_url = self.routers['assets'] + urlencode(params, quote_via=quote)
        self.logger.info(f"Requesting URL: {equity_url}")
        yield scrapy.Request(equity_url, callback=self.parse, 
                             meta={'page': 1, 'params': params}, dont_filter=True)

    def parse(self, response, **kwargs):
        self.logger.info(f"Parsing response from {response.url}")
        self.logger.info(f"Response status: {response.status}")
        self.logger.info(f"Response headers: {response.headers}") 
        try:
            # 检查响应是否被压缩
            body = (
                gzip.decompress(response.body)
                if response.headers.get('Content-Encoding') == b'gzip'
                else response.body
            )

            content = json.loads(body)
            self.logger.info(f"Parsed JSON content: {content}")
            
            if 'data' not in content:
                self.logger.error(f"No 'data' field in response: {content}")
                return
                
            diff = content['data'].get('diff', [])
            self.logger.info(f"Found {len(diff)} items in response")
            
            if not diff:
                self.logger.warning("No data found in response")
                return
            
            # set loader
            for _, obj in diff.items():
                try:
                    self.logger.info(f"Processing item: {obj}")
                    asset = ItemLoader(item=AssetItem())
                    asset.add_value('sid', obj['f12'])
                    asset.add_value('name', obj['f14'])
                    asset.add_value('first_trading', obj['f26'])
                    
                    item = asset.load_item()
                    # self.logger.info(f"Yielding item: {item}")
                    yield item
                except KeyError as e:
                    self.logger.error(f"Missing key in object: {e}, object: {obj}")
                except Exception as e:
                    self.logger.error(f"Error processing item: {e}, object: {obj}")
            
            # next page
            meta = response.meta
            meta['page'] += 1
            params = meta['params']
            params['pn'] = meta['page']
            equity_url = self.routers['assets'] + urlencode(params, quote_via=quote)
            self.logger.info(f"Requesting next page: {equity_url}")

            # yield scrapy.Request(equity_url, callback=self.parse, 
            #                      meta={'page': meta['page'], 'params': params}, dont_filter=True)

        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse JSON response: {e}")
            self.logger.error(f"Response body: {response.body[:1000]}")
        except Exception as e:
            self.logger.error(f"Unexpected error in parse: {e}")
            self.logger.error(f"Response body: {response.body[:1000]}")
