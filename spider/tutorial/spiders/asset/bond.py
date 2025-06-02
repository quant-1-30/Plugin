# !/usr/bin/env python3
# -*- coding : utf-8 -*-
"""
Created on Tue Mar 12 15:37:47 2019

@author: python
"""
import scrapy
import json
from scrapy.loader import ItemLoader
from urllib.parse import urlencode, quote

from tutorial.items import BondItem
from tutorial.base import BaseSpider


class Bond(BaseSpider):
    """
        回售最后2年70%, 赎回130%  type=KZZ_HSSH
    """
    name = 'bond'
    allowed_domains = ['dcfm.eastmoney.com', 'push2his.eastmoney.com']

    # custom_settings = {
    #     'SOME_SETTING': 'some value',
    # }
    def start_requests(self):
        params = {'type': 'KZZ_MX',
                  'token': '894050c76af8597a853f5b408b759f5d'}
        # bond_url = Routers['bond'] + urlencode(params, quote_via=quote)
        bond_url = self.routers['bond'] + urlencode(params, quote_via=quote)
        yield scrapy.Request(bond_url, callback=self.parse, 
                             meta={'page': 1, 'params': params}, dont_filter=True)

    def parse(self, response, **kwargs):
        # set response meta
        meta = response.meta
        params = meta['params']
        # content
        content = json.loads(response.text)
        diff = content['data']['diff']
        print("parser", diff)
        if not diff:
            return

        # set loader
        asset = ItemLoader(item=BondItem())
        for _, obj in diff.items():
            asset.add_value('sid', obj['f12'])
            asset.add_value('name', obj['f14'])
            asset.add_value('swap_code', obj['f16'])
            asset.add_value('swap_price', obj['f18'])
            asset.add_value('swap_sdate', obj['f20'])
            asset.add_value('swap_edate', obj['f22'])

        items = asset.load_item()
        yield items
        
        # next page
        meta['page'] += 1
        params['pn'] = meta['page']
        equity_url = self.routers['assets'] + urlencode(params, quote_via=quote)
        yield scrapy.Request(equity_url, callback=self.parse, 
                             meta={'page': meta['page'], 'params': params}, dont_filter=True)

