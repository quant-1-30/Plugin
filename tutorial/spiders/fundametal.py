# !/usr/bin/env python3
# -*- coding : utf-8 -*-
"""
Created on Tue Mar 12 15:37:47 2019

@author: python
"""
import scrapy, json
from scrapy import  Selector
from scrapy.spiders import CrawlSpider
from urllib.parse import urlencode, quote
from scrapy.loader import ItemLoader
from itemloaders.processors import MapCompose
from test.items import BasicsItem, Dividends, Rigths, Ownership


class Basics(CrawlSpider):
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
    name = 'basics'
    allowed_domains = ['push2.eastmoney.com', 'finance.sina.com.cn', 'push2his.eastmoney.com']
    handle_httpstatus_list = [301, 302]

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super(Basics, cls).from_crawler(crawler, *args, **kwargs)
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
        # handle_httpstatus_all
        meta['dont_redirect'] = True
        meta['dont_retry'] = False
        meta['dont_filter'] = True
        content = json.loads(response.text)
        for name, obj in content['data']['diff'].items():
            symbol = obj['f12']
            meta['sid'] = symbol
            asset = 'sh' + symbol if symbol.startswith('6') else 'sz' + symbol
            url_basics = self.routers['basics'] % asset
            # load basics
            yield scrapy.Request(url=url_basics, meta=meta, callback=self._parse, dont_filter=True)

    def _parse(self, response, **kwargs):
        meta = response.meta
        target = response.xpath("//div[@class='sec_title']/h3[contains(., '%s')]/a/@href" % '公司资料').getall()
        if target:
            yield response.follow(url=target[0], meta=meta, callback=self._parse_basics, dont_filter=True)

    def _parse_basics(self, response, **kwargs):
        # div[@id='con02-0']/
        meta = response.meta
        # set loader
        l_basics = ItemLoader(item=BasicsItem(), response=response)
        # load basics
        l_basics.add_value('owner', 'basics')
        l_basics.add_value('sid', meta['sid'])
        l_basics.add_xpath('name', "//table[@id='comInfo1']/tr[contains(., '公司名称')]/td[@class='ccl']/text()",
                           MapCompose(str.strip))
        l_basics.add_xpath('market', "//table[@id='comInfo1']/tr[contains(., '上市市场')]/td[@class='cc'][1]/text()")
        l_basics.add_xpath('ipo_date', "//table[@id='comInfo1']/tr[contains(., '上市日期')]/td[@class='cc']/a/text()")
        l_basics.add_xpath('ipo_price', "//table[@id='comInfo1']/tr[contains(., '发行价格')]/td[@class='cc'][1]/text()")
        l_basics.add_xpath('broker', "//table[@id='comInfo1']/tr[contains(., '主承销商')]/td[@class='cc']/a/text()")
        l_basics.add_xpath('district_code', "//table[@id='comInfo1']/tr[contains(., '邮政编码')]/td[@class='cc']/text()")
        basics = l_basics.load_item()
        # yield basics and filter stock which has not come to market
        if basics.get('ipo_date', None):
            yield basics
            # load dividends
            target = response.xpath("//div[@class='sec_title']/h3[contains(., '%s')]/a/@href" % '发行分配').getall()[0]
            yield response.follow(url=target, meta=meta, callback=self._parse_dividends, dont_filter=True)

    def _parse_dividends(self, response, **kwargs):
        meta = response.meta
        # set loader
        l_dividends = ItemLoader(item=Dividends(), response=response)
        # load dividends
        l_dividends.add_value('owner', 'dividends')
        l_dividends.add_value('sid', meta['sid'])
        l_dividends.add_xpath('declare_date', "//table[@id='sharebonus_1']/tbody/tr/td[1]/text()")
        l_dividends.add_xpath('bonus', "//table[@id='sharebonus_1']/tbody/tr/td[2]/text()")
        l_dividends.add_xpath('transfer', "//table[@id='sharebonus_1']/tbody/tr/td[3]/text()")
        l_dividends.add_xpath('interest', "//table[@id='sharebonus_1']/tbody/tr/td[4]/text()")
        l_dividends.add_xpath('progress', "//table[@id='sharebonus_1']/tbody/tr/td[5]/text()")
        l_dividends.add_xpath('ex_date', "//table[@id='sharebonus_1']/tbody/tr/td[6]/text()")
        l_dividends.add_xpath('register_date', "//table[@id='sharebonus_1']/tbody/tr/td[7]/text()")
        l_dividends.add_xpath('market_date', "//table[@id='sharebonus_1']/tbody/tr/td[8]/text()")
        yield l_dividends.load_item()
        # 判断是否存在
        obj = Selector(text=response.text).xpath("//table[@id='sharebonus_2']/tbody/tr[contains(., '暂时没有数据')]/td/text()").getall()
        if not len(obj):
            l_rights = ItemLoader(item=Rigths(), response=response)
            l_rights.add_value('owner', 'rights')
            l_rights.add_value('sid', meta['sid'])
            l_rights.add_xpath('declare_date', "//table[@id='sharebonus_2']/tbody/tr/td[1]/text()")
            l_rights.add_xpath('bonus', "//table[@id='sharebonus_2']/tbody/tr/td[2]/text()")
            l_rights.add_xpath('price', "//table[@id='sharebonus_2']/tbody/tr/td[3]/text()")
            l_rights.add_xpath('benchmark', "//table[@id='sharebonus_2']/tbody/tr/td[4]/text()")
            l_rights.add_xpath('ex_date', "//table[@id='sharebonus_2']/tbody/tr/td[5]/text()")
            l_rights.add_xpath('register_date', "//table[@id='sharebonus_2']/tbody/tr/td[6]/text()")
            l_rights.add_xpath('market_date', "//table[@id='sharebonus_2']/tbody/tr/td[9]/text()")
            yield l_rights.load_item()
        # target = response.xpath("//div[@class='Menu-Con']/tr/td[contains(., '%s')]/a/@href" % '股本结构').getall()[0]
        target = response.xpath("//tr/td[contains(., '%s')]/a/@href" % '股本结构').getall()[0]
        # load ownership
        yield response.follow(url=target, meta=meta, callback=self._parse_ownership, dont_filter=True)

    @staticmethod
    def _parse_ownership(response, **kwargs):
        meta = response.meta
        # set loader
        l_ownership = ItemLoader(item=Ownership(), response=response)
        # load ownership
        l_ownership.add_value('owner', 'ownership')
        l_ownership.add_value('sid', meta['sid'])
        l_ownership.add_xpath('change_date', "//table/tbody/tr[contains(., '变动日期')]/td/text()")
        # l_ownership.add_xpath('declare_date',  "//table/tbody/tr[contains(., '公告日期')]/td/text()")
        l_ownership.add_xpath('general', "//table/tbody/tr[contains(., '总股本')]/td/text()",
                              MapCompose(lambda x: x.split('万股')[0], str.strip))
        l_ownership.add_xpath('float', "//table/tbody/tr[contains(., '流通A股')]/td/text()",
                              MapCompose(lambda x: x.split('万股')[0], str.strip))
        l_ownership.add_xpath('strict', "//table/tbody/tr[contains(., '限售A股')]/td/text()",
                              MapCompose(lambda x: x.split('万股')[0], str.strip))
        yield l_ownership.load_item()
