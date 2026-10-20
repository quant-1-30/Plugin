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

import os
from dotenv import load_dotenv

load_dotenv()

BOT_NAME = 'backtest'

# Obey robots.txt rules
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
          'Accept-Encoding': 'gzip',
          'Accept-Language': 'zh-CN,zh;q=0.9, en',
          'Connection': 'keep-alive'}

# proxy (read from .env to avoid hardcoding sensitive credentials)
_proxy_env = os.getenv('USER_PROXY_IP', '')
USER_PROXY_IP = [p.strip() for p in _proxy_env.split(',') if p.strip()]

HTTPPROXY_ENABLED = bool(USER_PROXY_IP)

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
HTTPERROR_ALLOWED_CODES = []

# Enable or disable spider middlewares
SPIDER_MIDDLEWARES = {
    'scrapy.spidermiddlewares.httperror.HttpErrorMiddleware': None,
    'scrapy.spidermiddlewares.offsite.OffsiteMiddleware': None,
    'scrapy.spidermiddlewares.referer.RefererMiddleware': None,
    'scrapy.spidermiddlewares.urllength.UrlLengthMiddleware': None,
    'scrapy.spidermiddlewares.depth.DepthMiddleware': None,
    'spider.middlewares.HttpErrorMiddleware': 50,
    'spider.middlewares.ErrorSpiderMiddleware': 500,
}

# Enable or disable extensions
# See https://docs.scrapy.org/en/latest/topics/extensions.html
EXTENSIONS = {
   'scrapy.extensions.corestats.CoreStats': None,
   'scrapy.extensions.logstats.LogStats': None,
   'spider.extensions.StatsMailer': 100,
   'spider.extensions.CoreStats': 0,
}

POSTGRES_BATCH_SIZE = int(os.getenv('POSTGRES_BATCH_SIZE', 100))

# Configure item pipelines (overridden per spider in custom_settings)
ITEM_PIPELINES = {}

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

LOG_LEVEL = 'INFO'

# mail (MAIL_PASS 由 StatsMailer 直接从环境变量读取，避免在 Scrapy Overridden settings 日志中明文打印)
MAIL_HOST = os.getenv('MAIL_HOST', 'smtp.163.com')
MAIL_FROM = os.getenv('MAIL_FROM', '')
MAIL_USER = os.getenv('MAIL_USER', '')
MAIL_PORT = int(os.getenv('MAIL_PORT', 465))
MAIL_SSL = bool(int(os.getenv('MAIL_SSL', 1)))
_rcpts_env = os.getenv('STATSMAILER_RCPTS', '')
STATSMAILER_RCPTS = [r.strip() for r in _rcpts_env.split(',') if r.strip()]
