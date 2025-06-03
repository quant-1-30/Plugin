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

from tutorial.items import BondItem
from tutorial.base import BaseSpider

__all__ = ['Bond']


class Bond(BaseSpider):
    """
        回售最后2年70%, 赎回130%  type=KZZ_HSSH
    """
    name = 'bond'
    allowed_domains = ['dcfm.eastmoney.com', 'push2his.eastmoney.com']

    # custom_settings = {
    #     'SOME_SETTING': 'some value',
    # }
    async def start(self):
        params = {'type': 'KZZ_MX',
                  'token': '894050c76af8597a853f5b408b759f5d'}
        start_url = self.routers['bond'] + urlencode(params, quote_via=quote)
        yield scrapy.Request(start_url, callback=self.parse, 
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
                bond = ItemLoader(item=BondItem())
                bond.add_value('sid', obj['f12'])
                bond.add_value('name', obj['f14'])
                bond.add_value('swap_code', obj['f16'])
                bond.add_value('swap_price', obj['f18'])
                bond.add_value('swap_sdate', obj['f20'])
                bond.add_value('swap_edate', obj['f22'])
    
                item = bond.load_item()
                yield item
            
            # next page
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
