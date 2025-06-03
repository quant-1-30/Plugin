# !/usr/bin/env python3
# -*- coding : utf-8 -*-
"""
Created on Tue Mar 12 15:37:47 2019

@author: python
"""
import gzip
import scrapy
import json
from scrapy.loader import ItemLoader
from urllib.parse import urlencode, quote

from tutorial.items import DualItem
from tutorial.base import BaseSpider

__all__ = ['Dual']


class Dual(BaseSpider):

    name = 'dual'
    table_name = "asset"
    allowed_domains = ['push2.eastmoney.com', 'push2his.eastmoney.com']

    # custom_settings = {
    #     'SOME_SETTING': 'some value',
    # }
    async def start(self):
        # load dual
        params = {'fs': 'b:DLMK0101',
                  'fields': 'f12,f191,f14',
                  'pn': 1,
                  'pz': 100}
        # dual_url = Routers['universe'] + urlencode(params, quote_via=quote)
        start_url = self.routers['assets'] + urlencode(params, quote_via=quote)
        yield scrapy.Request(start_url,  callback=self.parse, 
                             meta={'page': 1, 'params': params, 'retry_count': 0}, 
                             errback=self.errback_httpbin,
                             dont_filter=True)

    def parse(self, response, **kwargs):
        self.logger.info(f"Response headers: {response.headers} url: {response.url} and status: {response.status}")
        try:
            # 检查响应是否被压缩
            body = (
                gzip.decompress(response.body)
                if response.headers.get('Content-Encoding') == b'gzip'
                else response.body
            )
            # content
            content = json.loads(body)
            diff = content['data'].get('diff', {})
            if not diff:
                return
            
            for _, obj in diff.items():
                dual = ItemLoader(item=DualItem())
                dual.add_value('sid', obj['f12'])
                dual.add_value('name', obj['f14'])
                dual.add_value('dual', obj['f16'])

                item = dual.load_item()
                yield item
            
            # next page
            # set response meta
            meta = response.meta
            params = meta['params']
            meta['page'] += 1
            params['pn'] = meta['page']
            next_url = self.routers['assets'] + urlencode(params, quote_via=quote)
            yield scrapy.Request(next_url, callback=self.parse, 
                                 meta={'page': meta['page'], 'params': params, 'retry_count': 0}, 
                                 errback=self.errback_httpbin,
                                 dont_filter=True)
        except Exception as e:
            self.logger.error(f"Unexpected error in parse: {e}")
            return self._retry_request(response)
