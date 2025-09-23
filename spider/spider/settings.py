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

BOT_NAME = 'backtest'

# Obey robots.txt rules
ROBOTSTXT_OBEY = False
ROBOTSTXT_OBEY = False

# 添加异步支持
TWISTED_REACTOR = 'twisted.internet.asyncioreactor.AsyncioSelectorReactor'

SPIDER_MODULES = ['spider.crawlers']
NEWSPIDER_MODULE = 'spider.crawlers'

# Crawl responsibly by identifying yourself (and your website) on the user-agent
USER_AGENT = ['Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_6) AppleWebKit/605.1.15'
              '(KHTML, like Gecko) Version/13.1.2 Safari/605.1.15',
              'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_3) AppleWebKit/537.36 '
              '(KHTML, like Gecko) Chrome/79.0.3945.130 Safari/537.36',
              'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 '
              '(KHTML, like Gecko) Chrome/79.0.3945.130 Safari/537.36']

# Override the default request headers:
DEFAULT_REQUEST_HEADERS = {
          'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
          'Accept-Encoding': 'gzip, deflate',
          'Accept-Language': 'zh-CN,zh;q=0.9, en',
          'Connection': 'keep-alive'}

# proxy
USER_PROXY_IP = ['http://mylh05w9:mylh05w9@49.67.73.93:2018',
            'http://mylh05w8:mylh05w8@218.93.9.13:2021',
            'http://mylh05w7:mylh05w7@180.97.244.253:2018',
            'http://mylh05w6:mylh05w6@36.150.45.208:2018',
            'http://mylh05w5:mylh05w5@221.229.107.77:2018',
            'http://mylh05w4:mylh05w4@117.62.237.178:2729',
            'http://mylh05w3:mylh05w3@121.229.44.134:8225',
            'http://mylh05w2:mylh05w2@101.89.216.66:110',
            'http://mylh05w1:mylh05w1@60.190.234.153:2018']

HTTPPROXY_ENABLED = True

# Configure a delay for requests for the same website (default: 0)
# See https://docs.scrapy.org/en/latest/topics/settings.html#download-delay
# See also autothrottle settings and docs
DOWNLOAD_DELAY = 0.5
RANDOMIZE_DOWNLOAD_DELAY = True


# Disable cookies (enabled by default)
# disable cookies (see COOKIES_ENABLED) as some sites may use cookies to spot bot behaviour
COOKIES_ENABLED = False
COOKIES_DEBUG = False

# Disable Telnet Console (enabled by default)
TELNETCONSOLE_ENABLED = False

# redirect 301 302
REDIRECT_ENABLED = False
REDIRECT_MAX_TIMES = 1

# default 180
DOWNLOAD_TIMEOUT = 30

# stats
DOWNLOADER_STATS = True

# Configure retryMiddle
RETRY_ENABLED = True
RETRY_TIMES = 5
RETRY_HTTP_CODES = [408, 429, 456, 500, 502, 503, 504, 522, 524]
# delay to process
RETRY_PRIORITY_ADJUST = -1

# Enable or disable downloader middlewares
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
DOWNLOADER_MIDDLEWARES = {
    'scrapy.downloadermiddlewares.useragent.UserAgentMiddleware': None,
    'scrapy.downloadermiddlewares.retry.RetryMiddleware': None,
    'scrapy.downloadermiddlewares.redirect.RedirectMiddleware': None,
    'scrapy.downloadermiddlewares.httpcompression.HttpCompressionMiddleware': None,
    'scrapy.downloadermiddlewares.stats.DownloaderStats': None,
}

# RFC2616 policy --- This policy provides a RFC2616 compliant HTTP cache, i.e. with HTTP Cache-Control awareness,
# aimed at production and used in continuous runs to avoid downloading unmodified data (to save bandwidth and speed up)

# httperror
HTTPERROR_ALLOW_ALL = False
HTTPERROR_ALLOWED_CODES = [301, 302]

# Enable or disable spider middlewares
SPIDER_MIDDLEWARES = {
    'scrapy.spidermiddlewares.httperror.HttpErrorMiddleware': None,
    'scrapy.spidermiddlewares.offsite.OffsiteMiddleware': None,
    'scrapy.spidermiddlewares.referer.RefererMiddleware': None,
    'scrapy.spidermiddlewares.urllength.UrlLengthMiddleware': None,
    'scrapy.spidermiddlewares.depth.DepthMiddleware': None,
    'spider.middlewares.ErrorSpiderMiddleware': 500,
}

# Enable or disable extensions
# See https://docs.scrapy.org/en/latest/topics/extensions.html
EXTENSIONS = {
   'scrapy.extensions.logstats.LogStats': None,
   'spider.extensions.StatsMailer': None,
   'spider.extensions.CoreStats': 0,
}

# Configure item pipelines
# https://docs.scrapy.org/en/latest/topics/item-pipeline.html
ITEM_PIPELINES = {
   #  'spider.pipelines.BasicsPipeline': 300,
   #  'spider.pipelines.AlignPipeline': 400,
    # 'spider.pipelines.AsyncDb': 500,
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

# Configure maximum concurrent requests performed by Scrapy (default: 16)
CONCURRENT_REQUESTS = 32
# The download delay setting will honor only one of:
CONCURRENT_REQUESTS_PER_DOMAIN = 16
# None zero CONCURRENT_REQUESTS_PER_DOMAIN is ignored
CONCURRENT_REQUESTS_PER_IP = 16

# Enable and configure HTTP caching (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html#httpcache-middleware-settings
# HTTPCACHE_ENABLED = True
# HTTPCACHE_EXPIRATION_SECS = 0
# HTTPCACHE_DIR = 'httpcache'
# HTTPCACHE_IGNORE_HTTP_CODES = []
# HTTPCACHE_STORAGE = 'scrapy.extensions.httpcache.FilesystemCacheStorage'

# set log
# LOG_FILE = 'logs/{s}.log'.format(s=datetime.datetime.now().strftime('%Y%m%d_%H:%M:%S'))
LOG_LEVEL = 'INFO'

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

# SPIDER_MIDDLEWARES_BASE = {
#     'scrapy.spidermiddlewares.httperror.HttpErrorMiddleware': 50,
#     'scrapy.spidermiddlewares.offsite.OffsiteMiddleware': 500,
#     'scrapy.spidermiddlewares.referer.RefererMiddleware': 700,
#     'scrapy.spidermiddlewares.urllength.UrlLengthMiddleware': 800,
#     'scrapy.spidermiddlewares.depth.DepthMiddleware': 900,
# }

# # Enable or disable spider middlewares default
# DOWNLOADER_MIDDLEWARES_BASE = {
#     'scrapy.downloadermiddlewares.robotstxt.RobotsTxtMiddleware': 100,
#     'scrapy.downloadermiddlewares.httpauth.HttpAuthMiddleware': None,
#     'scrapy.downloadermiddlewares.downloadtimeout.DownloadTimeoutMiddleware': None,
#     'scrapy.downloadermiddlewares.defaultheaders.DefaultHeadersMiddleware': None,
#     'scrapy.downloadermiddlewares.useragent.UserAgentMiddleware': None,
#     'scrapy.downloadermiddlewares.retry.RetryMiddleware': None,
#     'scrapy.downloadermiddlewares.ajaxcrawl.AjaxCrawlMiddleware': None,
#     'scrapy.downloadermiddlewares.redirect.MetaRefreshMiddleware': None,
#     'scrapy.downloadermiddlewares.httpcompression.HttpCompressionMiddleware': None,
#     'scrapy.downloadermiddlewares.redirect.RedirectMiddleware': None,
#     'scrapy.downloadermiddlewares.cookies.CookiesMiddleware': None,
#     'scrapy.downloadermiddlewares.httpproxy.HttpProxyMiddleware': None,
#     'scrapy.downloadermiddlewares.stats.DownloaderStats': None,
#     'scrapy.downloadermiddlewares.httpcache.HttpCacheMiddleware': None,
# }

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
