a.获取全部的资产标的 --- equity convertible etf
b.筛选出需要更新的标的（与缓存进行比较）
# 字段非string一定要单独进行格式处理
asset status 由于吸收合并代码可能会消失但是主体继续上市存在 e.g. T00018
对于暂停上市 delist_date 为None(作为一种长期停盘的情况来考虑，由于我们不能存在后视误差不清楚是否能重新上市）
基于算法发出信号操作暂时上市的标的, 为了避免前视误差，过滤筛选距离已经退市标的而不是暂停上市  e.g. 5个交易日的股票
对于暂停上市的股票可能还存在重新上市的可能性也可能存在退市的可能性 --- None ,状态不断的更新
sr=-1 --- 表示倒序 sr=1 --- 顺序 或者 sortRule format {} 过滤
科创板是我国首个实行注册制的板块，我们在看科创板行情的时候，会发现一些科创板的股票后面会带有一些字母，那么科创板字母代表什么呢?

我们经常看到的科创板股票字母有N、C、U、W、V, 它们分别有一下含义:

N表示科创板新股上市的第一天,C表示新股上市次日到第五天之间。科创板新股第一到第五个交易日无涨跌幅限制。

U表示发行人尚未盈利。科创板实行注册制, 上市标准丰富,未盈利的企业也可以上市。

W则代表发行人具有表决权差异安排。

V则代表发行人具有协议控制架构或者类似特殊安排。

D就说明公司是以CDR(中国存托凭证)形式登陆科创板。

除了科创板之外，创业板企业也有以上字母表达相同样的含义。

科创板创业板也是有ST制度的, 但是这两个板块的退市标准相对于主板存在一定的差异。而且即便科创板\创业板企业出现了退市警示，
涨跌幅限制依旧是20%》。

This package will contain the spiders of your Scrapy project

Please refer to the documentation for information on how to create and manage
your spiders.

generic spiders based on certain rules Sitemaps Xml or Csv feed
CrawlerSpider following links by a set of rules

Item ItemLoader

Item Pipeline

Downloader Middleware
CookieMiddleware  DefaultHeadersMiddleware  DownloadTimeoutMiddleware HttpAuthMiddleware
UserAgentMiddleware RobotParser RetryMiddleware RedirectMiddleware HttpProxyMiddleware
HttpCacheMiddleware httpcache DummyPolicy --- cache no awareness ;  RFC2616Policy --- production


Spider MiddleWare
DepthMiddleware  HttpErrorMiddleware  OffsiteMiddleware  UrlLengthMiddleware
RefererMiddleware --- no-referrer | no-referrer-when-downgrade | origin | origin-when-cross-origin
same-origin | strict-origin | strict-origin-when-cross-origin | unsafe-url

Signals
return deferred objects --- engine_started engine_stopped item_scraped item_dropped
return deferred objects --- item_error spider_opened spider_closed
no return --- spider_idle  spider_error  request_scheduled request_dropped  request_
no return --- reached_downloader request_left_downloader  response_downloaded response_received

asyncio | twisted

run scrapy from scripts  CrawlerProcess --- run multiple scrapy crawlers
CrawlerRunner --- addBoth , reactor ;

extensions --- Typically, extensions connect to signals and perform tasks triggered by them.
LogStats  CoreStats TelnetConsole CloseSpider

Job pausing and resuming --- job -- jobdir

memory leak  --- utils.trackref

request.request_fingerprint (accept request return fingerprint)

Spiders Contracts

scrapy.extensions.httpcache.RFC2616Policy

DUPEFILTER_CLASS = 'scrapy.dupefilters.RFPDupeFilter'

broad crawler
scrapy startproject test

无头浏览器
from selenium.webdriver import Chrome
drive = Chrome()
obj = drive.get(ths)
input = drive.find_element_by_link_text('002570')
search = drive.find_element_by_id('su')
input.send_keys('002570.SZ')
search.click()

import re, json
from ..items import KlineItem
from scrapy.loader import ItemLoader
from urllib.parse import urlencode, quote

scrapy.mail.MailSender(smtphost=None, mailfrom=None, smtpuser=None, smtppass=None, smtpport=None)[source]
Parameters
smtphost (str or bytes) – the SMTP host to use for sending the emails. If omitted, the MAIL_HOST setting will be used.

mailfrom (str) – the address used to send emails (in the From: header). If omitted, the MAIL_FROM setting will be used.

smtpuser – the SMTP user. If omitted, the MAIL_USER setting will be used. If not given, no SMTP authentication will be performed.

smtppass (str or bytes) – the SMTP pass for authentication.

smtpport (int) – the SMTP port to connect to

smtptls (bool) – enforce using SMTP STARTTLS

smtpssl (bool) – enforce using a secure SSL connection

