# !/usr/bin/env python3
# -*- coding : utf-8 -*-
"""
Created on Tue Mar 12 15:37:47 2019

@author: python
"""
import scrapy, json
from scrapy.spiders import CrawlSpider
from urllib.parse import urlencode, quote
from scrapy.loader import ItemLoader
from test.utils import params2url, parse_kline
from test.items import AssetItem


class Stock(CrawlSpider):
    """
        a.获取全部的资产标的 --- equity convertible etf
        b.筛选出需要更新的标的（与缓存进行比较）
        # 字段非string一定要单独进行格式处理
        asset status 由于吸收合并代码可能会消失但是主体继续上市存在 e.g. T00018
        对于暂停上市 delist_date 为None(作为一种长期停盘的情况来考虑，由于我们不能存在后视误差不清楚是否能重新上市）
        基于算法发出信号操作暂时上市的标的, 为了避免前视误差，过滤筛选距离已经退市标的而不是暂停上市  e.g. 5个交易日的股票；
        对于暂停上市的股票可能还存在重新上市的可能性也可能存在退市的可能性 --- None ,状态不断的更新
        sr=-1 --- 表示倒序 ； sr=1 --- 顺序 或者 sortRule format {} 过滤
        科创板是我国首个实行注册制的板块，我们在看科创板行情的时候，会发现一些科创板的股票后面会带有一些字母，那么科创板字母代表什么呢?

        我们经常看到的科创板股票字母有N、C、U、W、V，它们分别有一下含义：

        【1】N表示科创板新股上市的第一天,C表示新股上市次日到第五天之间。科创板新股第一到第五个交易日无涨跌幅限制。

        【2】U表示发行人尚未盈利。科创板实行注册制，上市标准丰富，未盈利的企业也可以上市。

        【3】W则代表发行人具有表决权差异安排。

        【4】V则代表发行人具有协议控制架构或者类似特殊安排。

        【5】D就说明公司是以CDR(中国存托凭证)形式登陆科创板。

        除了科创板之外，创业板企业也有以上字母表达相同样的含义。

        值得一提的是，科创板创业板也是有ST制度的，但是这两个板块的退市标准相对于主板存在一定的差异。而且，即便科创板、创业板企业出现了退市警示，
        涨跌幅限制依旧是20%》。
    """
    name = 'stock'
    allowed_domains = ['push2.eastmoney.com', 'finance.sina.com.cn', 'push2his.eastmoney.com']
    handle_httpstatus_list = [301, 302]

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super(Stock, cls).from_crawler(crawler, *args, **kwargs)
        routers = crawler.settings.get(
            'FILES_URLS_FIELD')
        spider.routers = routers
        return spider

    def start_requests(self):
        params = {'fs': 'm:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23',
                  'fields': 'f12,f14',
                  'pn': 1,
                  'pz': 50000}
        equity_url = self.routers['universe'] + urlencode(params, quote_via=quote)
        yield scrapy.Request(equity_url, callback=self.parse, dont_filter=True)

    def parse(self, response, **kwargs):
        # set response meta
        meta = response.meta
        meta['owner'] = 'equity'
        content = json.loads(response.text)
        # set loader
        equity = ItemLoader(item=AssetItem())
        equity.add_value('owner', meta['owner'])
        # load assets
        for name, obj in content['data']['diff'].items():
            equity.add_value('sid', obj['f12'])
            equity.add_value('name', obj['f14'])
        items = equity.load_item()
        yield items
        # load kline
        for symbol in items['sid']:
            meta['sid'] = symbol
            url_kline = params2url(meta['sid'])
            yield scrapy.Request(url_kline, meta=meta, callback=parse_kline, dont_filter=True)
