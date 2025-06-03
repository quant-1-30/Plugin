# !/usr/bin/env python3
# -*- coding : utf-8 -*-
"""
Created on Tue Mar 12 15:37:47 2019

@author: python
"""
import gzip
import scrapy
import json
from urllib.parse import urlencode, quote
from scrapy.loader import ItemLoader

from tutorial.items import KlineItem
from tutorial.base import BaseSpider

__all__ = ['Kline']


class Kline(BaseSpider):

    name = 'kline'
    table_name = "tick"
    allowed_domains = ['push2.eastmoney.com', 'finance.sina.com.cn', 'push2his.eastmoney.com']
    handle_httpstatus_list = [301, 302]
    
    # custom_settings = {
    #     'SOME_SETTING': 'some value',
    # }

    async def start(self):
        params = {'fs': 'm:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23',
                  'fields': 'f12,f14,f26',
                  'pn': 1,
                  'pz': 50000}
        start_url = self.routers['assets'] + urlencode(params, quote_via=quote)
        yield scrapy.Request(start_url, callback=self.parse, 
                             meta={'page': 1, 'params': params, 'retry_count': 0}, 
                             errback=self.errback_httpbin,
                             dont_filter=True)
        
    def parse(self, response, **kwargs):
        self.logger.info(f"Response headers: {response.headers} url: {response.url} and status: {response.status}")
        meta = response.meta
        meta['retry_count'] = 0
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
                symbol = obj['f12']
                asset = 'sh' + symbol if symbol.startswith('6') else 'sz' + symbol
                url_kline = self.routers['kline'] % asset
                meta['sid'] = symbol
                yield scrapy.Request(url=url_kline, meta=meta.copy(), dont_filter=True, 
                                     callback=self._decode, 
                                     errback=self.errback_httpbin)

            # next stock page
            params = meta['params']
            meta['page'] += 1
            params['pn'] = meta['page']
            next_url = self.routers['assets'] + urlencode(params, quote_via=quote)
            yield scrapy.Request(next_url, callback=self.parse, 
                                 meta={'page': meta['page'], 'params': params}, dont_filter=True)
        except Exception as e:
            self.logger.error(f"Unexpected error in parse: {e}")
            # Retry on unexpected errors
            return self._retry_request(response)

    def _decode(self, response, **kwargs):
        meta = response.meta
        sid = meta['sid']
        try:
            # 检查响应是否被压缩
            body = (
                gzip.decompress(response.body)
                if response.headers.get('Content-Encoding') == b'gzip'
                else response.body
            )
            # content
            content = json.loads(body)
            klines = content['data'].get('klines', [])
            if not klines:
                return

            for obj in klines:
                kline = ItemLoader(item=KlineItem())
                items = obj.split(',')
                kline.add_value('trade_dt', items[0])
                kline.add_value('open', items[1])
                kline.add_value('close', items[2])
                kline.add_value('high', items[3])
                kline.add_value('low', items[4])
                kline.add_value('volume', items[5])
                kline.add_value('amount', items[6])
                kline.add_value('amplitude', items[7])
                kline.add_value('pct', items[8])
                kline.add_value('change', items[9])
                kline.add_value('turnover', items[10])
                kline.add_value('sid', sid)
                item = kline.load_item()
                yield item
        except Exception as e:
            self.logger.error(f"Unexpected error in _decode: {e}")
            # Retry on unexpected errors
            return self._retry_request(response)
