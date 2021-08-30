# !/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Mar 12 15:37:47 2019

@author: python
"""
# Scrapy settings for test project
#
# For simplicity, this file contains only settings considered important or
# commonly used. You can find more settings consulting the documentation:
#
#     https://docs.scrapy.org/en/latest/topics/settings.html
#     https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
#     https://docs.scrapy.org/en/latest/topics/spider-middleware.html
import datetime

# 是否初始化
Initialize = False

# 数据库配置
MYSQL = {
    'username': 'root',
    'password': 'macpython',
    'host': 'localhost',
    'port': 3306,
    'db': 'arkquant',
    'pool_size': 100,
    'max_overflow': 100,
    # 'charset': 'utf-8'
}


BOT_NAME = 'ArkQuant'

SPIDER_MODULES = ['test.spiders']
NEWSPIDER_MODULE = 'test.spiders'


# Crawl responsibly by identifying yourself (and your website) on the user-agent
# USER_AGENT = 'test'

# Obey robots.txt rules
ROBOTSTXT_OBEY = False


# Configure a delay for requests for the same website (default: 0)
# See https://docs.scrapy.org/en/latest/topics/settings.html#download-delay
# See also autothrottle settings and docs
# DOWNLOAD_DELAY = 3


# Disable cookies (enabled by default)
# disable cookies (see COOKIES_ENABLED) as some sites may use cookies to spot bot behaviour
COOKIES_ENABLED = False
COOKIES_DEBUG = False

# Disable Telnet Console (enabled by default)
TELNETCONSOLE_ENABLED = False

# Override the default request headers:
DEFAULT_REQUEST_HEADERS = {
          'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
          'Accept-Encoding': 'gzip, deflate',
          'Accept-Language': 'zh-CN,zh;q=0.9, en',
          'Connection': 'keep-alive'}

# user_agents
USER_AGENT = ['Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_6) AppleWebKit/605.1.15'
              '(KHTML, like Gecko) Version/13.1.2 Safari/605.1.15',
              'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_3) AppleWebKit/537.36 '
              '(KHTML, like Gecko) Chrome/79.0.3945.130 Safari/537.36',
              'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 '
              '(KHTML, like Gecko) Chrome/79.0.3945.130 Safari/537.36']

# proxy
HTTPPROXY_ENABLED = False

# redirect 301 302
REDIRECT_ENABLED = False
REDIRECT_MAX_TIMES = 1

# default 180
DOWNLOAD_TIMEOUT = 1
# 0.5 * DOWNLOAD_DELAY and 1.5 * DOWNLOAD_DELAY
DOWNLOAD_DELAY = 1
RANDOMIZE_DOWNLOAD_DELAY = True
# stats
DOWNLOADER_STATS = True

# Configure retryMiddle
RETRY_ENABLED = True
RETRY_TIMES = 1
RETRY_HTTP_CODES = [408, 429, 456, 500, 502, 503, 504, 522, 524]


# Enable or disable downloader middlewares
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
DOWNLOADER_MIDDLEWARES = {
    'scrapy.downloadermiddlewares.useragent.UserAgentMiddleware': None,
    'scrapy.downloadermiddlewares.retry.RetryMiddleware': None,
    'test.middlewares.UserAgentMiddleware': 500,
    'test.middlewares.RetryMiddleware': 550,
    # 'scrapy.downloadermiddlewares.redirect.RedirectMiddleware': None,
    # 'test.middlewares.RedirectMiddleware': 600,
}

# Enable or disable spider middlewares
# DOWNLOADER_MIDDLEWARES_BASE = {
#     'scrapy.downloadermiddlewares.robotstxt.RobotsTxtMiddleware': 100,
#     'scrapy.downloadermiddlewares.httpauth.HttpAuthMiddleware': 300,
#     'scrapy.downloadermiddlewares.downloadtimeout.DownloadTimeoutMiddleware': 350,
#     'scrapy.downloadermiddlewares.defaultheaders.DefaultHeadersMiddleware': 400,
#     'scrapy.downloadermiddlewares.useragent.UserAgentMiddleware': 500,
#     'scrapy.downloadermiddlewares.retry.RetryMiddleware': 550,
#     'scrapy.downloadermiddlewares.ajaxcrawl.AjaxCrawlMiddleware': 560,
#     'scrapy.downloadermiddlewares.redirect.MetaRefreshMiddleware': 580,
#     'scrapy.downloadermiddlewares.httpcompression.HttpCompressionMiddleware': 590,
#     'scrapy.downloadermiddlewares.redirect.RedirectMiddleware': 600,
#     'scrapy.downloadermiddlewares.cookies.CookiesMiddleware': 700,
#     'scrapy.downloadermiddlewares.httpproxy.HttpProxyMiddleware': 750,
#     'scrapy.downloadermiddlewares.stats.DownloaderStats': 850,
#     'scrapy.downloadermiddlewares.httpcache.HttpCacheMiddleware': 900,
# }

# RFC2616 policy --- This policy provides a RFC2616 compliant HTTP cache, i.e. with HTTP Cache-Control awareness,
# aimed at production and used in continuous runs to avoid downloading unmodified data (to save bandwidth and speed up)


# httperror
HTTPERROR_ALLOW_ALL = False
HTTPERROR_ALLOWED_CODES = [301, 302]


SPIDER_MIDDLEWARES = {
   'scrapy.spidermiddlewares.httperror.HttpErrorMiddleware': None,
   'test.middlewares.ErrorSpiderMiddleware': 50,
}

# SPIDER_MIDDLEWARES_BASE = {
#     'scrapy.spidermiddlewares.httperror.HttpErrorMiddleware': 50,
#     'scrapy.spidermiddlewares.offsite.OffsiteMiddleware': 500,
#     'scrapy.spidermiddlewares.referer.RefererMiddleware': 700,
#     'scrapy.spidermiddlewares.urllength.UrlLengthMiddleware': 800,
#     'scrapy.spidermiddlewares.depth.DepthMiddleware': 900,
# }


# Enable or disable extensions
# See https://docs.scrapy.org/en/latest/topics/extensions.html

EXTENSIONS = {
   'test.extensions.StatsMailer': 0,
   'test.extensions.CoreStats': 0,
}


# EXTENSIONS_BASE = {
#     'scrapy.extensions.corestats.CoreStats': 0,
#     'scrapy.extensions.telnet.TelnetConsole': 0,
#     'scrapy.extensions.memusage.MemoryUsage': 0,
#     'scrapy.extensions.memdebug.MemoryDebugger': 0,
#     'scrapy.extensions.closespider.CloseSpider': 0,
#     'scrapy.extensions.feedexport.FeedExporter': 0,
#     'scrapy.extensions.logstats.LogStats': 0,
#     'scrapy.extensions.spiderstate.SpiderState': 0,
#     'scrapy.extensions.throttle.AutoThrottle': 0,
# }

# Configure item pipelines
# See https://docs.scrapy.org/en/latest/topics/item-pipeline.html
ITEM_PIPELINES = {
    'test.pipelines.BasicsPipeline': 300,
    'test.pipelines.AlignPipeline': 400,
    'test.pipelines.DbPipeline': 500,
}

# Enable and configure the AutoThrottle extension (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/autothrottle.html
AUTOTHROTTLE_ENABLED = True
# The initial download delay
AUTOTHROTTLE_START_DELAY = 1
# The maximum download delay to be set in case of high latencies
AUTOTHROTTLE_MAX_DELAY = 3
# The average number of requests Scrapy should be sending in parallel to
# each remote server
AUTOTHROTTLE_TARGET_CONCURRENCY = 3.0
# Enable showing throttling stats for every response received:
AUTOTHROTTLE_DEBUG = False

# Configure maximum concurrent requests performed by Scrapy (default: 16) fixed reverse to autothrottle
# CONCURRENT_REQUESTS = 32
# The download delay setting will honor only one of:
# CONCURRENT_REQUESTS_PER_DOMAIN = 8
# None zero CONCURRENT_REQUESTS_PER_DOMAIN is ignored
# CONCURRENT_REQUESTS_PER_IP = 8

# Enable and configure HTTP caching (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html#httpcache-middleware-settings
# HTTPCACHE_ENABLED = True
# HTTPCACHE_EXPIRATION_SECS = 0
# HTTPCACHE_DIR = 'httpcache'
# HTTPCACHE_IGNORE_HTTP_CODES = []
# HTTPCACHE_STORAGE = 'scrapy.extensions.httpcache.FilesystemCacheStorage'

# set log
LOG_FILE = 'log/{s}.log'.format(s=datetime.datetime.now().strftime('%Y%m%d_%H:%M:%S'))
LOG_LEVEL = 'DEBUG'

# mail
MAIL_HOST = 'smtp.163.com'
MAIL_FROM = '13776668123@163.com'
MAIL_USER = '13776668123@163.com'
MAIL_PASS = 'ICFHBPNBTZTKWLUO'
MAIL_PORT = 465
MAIL_SSL = True
# MAIL_PORT = 25
# MAIL_SSL = False
STATSMAILER_RCPTS = ['13776668123@163.com']

# router 由于内部定义的keys才可以从from_crawler获取 , 全局配置; 找一个无关紧要的配置项
FILES_URLS_FIELD = {
           'universe': 'http://push2.eastmoney.com/api/qt/clist/get?',
           'kline': 'http://push2his.eastmoney.com/api/qt/stock/kline/get?',
           'basics': 'http://finance.sina.com.cn/realstock/company/%s/nc.shtml',
           'bond': 'http://dcfm.eastmoney.com/em_mutisvcexpandinterface/api/js/get?'
            }

# kline
Params = {'fields1': 'f1\x2Cf2\x2Cf3\x2Cf4\x2Cf5\x2Cf6',
          'fields2': 'f51\x2Cf52\x2Cf53\x2Cf54\x2Cf55\x2Cf56\x2Cf57\x2Cf58\x2Cf59\x2Cf60\x2Cf61',
          'klt': 101,
          'fqt': 0,
          'beg': 0 if Initialize else int(datetime.datetime.now().strftime('%Y%m%d')),
          'end': 20500101}
