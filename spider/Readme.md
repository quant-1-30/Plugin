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

Deferred 是 Twisted 框架的核心概念之一，它提供了一种优雅的方式来处理异步操作，特别是在像 Scrapy 这样的事件驱动框架中
Deferred.addCallback / addErrback

alter table rightment alter column report_date set not null;
alter table rightment drop constraint uq_sid_ex_date_rightment;
alter table rightment add constraint uq_sid_report_date_rightment unique (sid, report_date);

Scrapy 的 FEEDS 设置保存数据，您需要确保返回的对象是 Scrapy 可以处理的类型（如字典或 Item 对象）

科创板是我国首个实行注册制的板块，N、C、U、W、V(创业板相同样的含义):

N表示科创板新股上市的第一天,C表示新股上市次日到第五天之间。科创板新股第一到第五个交易日无涨跌幅限制。

U表示发行人尚未盈利。科创板实行注册制, 上市标准丰富,未盈利的企业也可以上市。

W则代表发行人具有表决权差异安排。

V则代表发行人具有协议控制架构或者类似特殊安排。

D就说明公司是以CDR(中国存托凭证)形式登陆科创板。

科创板创业板有ST制度的, 但是这两个板块的退市标准相对于主板存在一定的差异。而且即便科创板\创业板企业出现了退市警示，涨跌幅限制依旧是20%

# register_date:登记日 ; ex_date:除权除息日 
# 股权登记日后的下一个交易日就是除权日或除息日，这一天购入该公司股票的股东不再享有公司此次分红配股
# 上交所证券的红股上市日为股权除权日的下一个交易日; 深交所证券的红股上市日为股权登记日后的第3个交易日
# bonus_share --- 送股 / transfer --- 转股 / bonus --- 股息

# register_date:登记日 ; ex_date:除权除息日; pay_date:除权除息日 ; effective_date:上市日期 
# 股权登记日后的下一个交易日就是除权日或除息日，这一天购入该公司股票的股东不再享有公司此次分红配股
# 上交所证券的红股上市日为股权除权日的下一个交易日; 深交所证券的红股上市日为股权登记日后的第3个交易日
# price --- 配股价格 / ratio --- 配股比例
