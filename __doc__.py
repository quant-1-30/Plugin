
# This package will contain the spiders of your Scrapy project
#
# Please refer to the documentation for information on how to create and manage
# your spiders.

# generic spiders based on certain rules Sitemaps Xml or Csv feed
# CrawlerSpider following links by a set of rules

# Item ItemLoader

# Item Pipeline

# Downloader Middleware
# CookieMiddleware  DefaultHeadersMiddleware  DownloadTimeoutMiddleware HttpAuthMiddleware
# UserAgentMiddleware RobotParser RetryMiddleware RedirectMiddleware HttpProxyMiddleware
# HttpCacheMiddleware httpcache DummyPolicy --- cache no awareness ;  RFC2616Policy --- production


# Spider MiddleWare
# DepthMiddleware  HttpErrorMiddleware  OffsiteMiddleware  UrlLengthMiddleware
# RefererMiddleware --- no-referrer | no-referrer-when-downgrade | origin | origin-when-cross-origin
# same-origin | strict-origin | strict-origin-when-cross-origin | unsafe-url

# Signals
# return deferred objects --- engine_started engine_stopped item_scraped item_dropped
# return deferred objects --- item_error spider_opened spider_closed
# no return --- spider_idle  spider_error  request_scheduled request_dropped  request_
# no return --- reached_downloader request_left_downloader  response_downloaded response_received

# asyncio | twisted

# run scrapy from scripts  CrawlerProcess --- run multiple scrapy crawlers
# CrawlerRunner --- addBoth , reactor ;

# extensions --- Typically, extensions connect to signals and perform tasks triggered by them.
# LogStats  CoreStats TelnetConsole CloseSpider

# Job pausing and resuming --- job -- jobdir

# memory leak  --- utils.trackref

# request.request_fingerprint (accept request return fingerprint)

# Spiders Contracts

# scrapy.extensions.httpcache.RFC2616Policy

# DUPEFILTER_CLASS = 'scrapy.dupefilters.RFPDupeFilter'

# broad crawler
# scrapy startproject test

# 无头浏览器
# from selenium.webdriver import Chrome
# drive = Chrome()
# obj = drive.get(ths)
# input = drive.find_element_by_link_text('002570')
# search = drive.find_element_by_id('su')
# input.send_keys('002570.SZ')
# search.click()

# import re, json
# from ..items import KlineItem
# from scrapy.loader import ItemLoader
# from urllib.parse import urlencode, quote

# scrapy.mail.MailSender(smtphost=None, mailfrom=None, smtpuser=None, smtppass=None, smtpport=None)[source]
# Parameters
# smtphost (str or bytes) – the SMTP host to use for sending the emails. If omitted, the MAIL_HOST setting will be used.
#
# mailfrom (str) – the address used to send emails (in the From: header). If omitted, the MAIL_FROM setting will be used.
#
# smtpuser – the SMTP user. If omitted, the MAIL_USER setting will be used. If not given, no SMTP authentication will be performed.
#
# smtppass (str or bytes) – the SMTP pass for authentication.
#
# smtpport (int) – the SMTP port to connect to
#
# smtptls (bool) – enforce using SMTP STARTTLS
#
# smtpssl (bool) – enforce using a secure SSL connection
