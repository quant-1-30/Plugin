# Define here the models for your spider middleware
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/spider-middleware.html
# useful for handling different item types with a single interface

import random
import base64
import logging
import numpy as np

from twisted.internet import defer
from twisted.internet.error import (
    ConnectError,
    ConnectionDone,
    ConnectionLost,
    ConnectionRefusedError,
    DNSLookupError,
    TCPTimedOutError,
    TimeoutError,
)

from twisted.web.client import ResponseFailed

from scrapy import signals

from scrapy.exceptions import NotConfigured
from logging import getLogger

from twisted.internet import defer
from twisted.internet.error import (
    ConnectError,
    ConnectionDone,
    ConnectionLost,
    ConnectionRefusedError,
    DNSLookupError,
    TCPTimedOutError,
    TimeoutError,
)
from twisted.web.client import ResponseFailed

from scrapy.core.downloader.handlers.http11 import TunnelError
from scrapy.exceptions import NotConfigured
from scrapy.utils.response import response_status_message
from w3lib.http import basic_auth_header
from utils.tools import get_retry_request

retry_logger = getLogger(__name__)

logger = logging.getLogger(__name__)

__all__ = ['HttpAuthMiddleware', 'UserAgentMiddleware', 'HttpProxyMiddleware', 'RedirectMiddleware', 'CustomRetryMiddleware']


class SpiderDownloaderMiddleware:
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the downloader middleware does not modify the
    # passed objects.

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_request(self, request, spider):
        # Called for each request that goes through the downloader
        # middleware.
        # Must either:
        # - return None: continue processing this request
        # - or return a Response object
        # - or return a Request object
        # - or raise IgnoreRequest: process_exception() methods of
        #   installed downloader middleware will be called
        return None

    def process_response(self, request, response, spider):
        # Called with the response returned from the downloader.

        # Must either;
        # - return a Response object
        # - return a Request object
        # - or raise IgnoreRequest
        return response

    def process_exception(self, request, exception, spider):
        # Called when a download handler or a process_request()
        # (from other downloader middleware) raises an exception.

        # Must either:
        # - return None: continue processing this exception
        # - return a Response object: stops process_exception() chain
        # - return a Request object: stops process_exception() chain
        pass

    def spider_opened(self, spider):
        spider.logger.info('Spider opened: %s' % spider.name)


class HttpAuthMiddleware:
    """Set Basic HTTP Authorization header
    (http_user and http_pass spider class attributes)"""

    @classmethod
    def from_crawler(cls, crawler):
        o = cls()
        crawler.signals.connect(o.spider_opened, signal=signals.spider_opened)
        return o

    def spider_opened(self, spider):
        usr = getattr(spider, 'http_user', '')
        pwd = getattr(spider, 'http_pass', '')
        if usr or pwd:
            self.auth = basic_auth_header(usr, pwd)

    def process_request(self, request, spider):
        auth = getattr(self, 'auth', None)
        if auth and b'Authorization' not in request.headers:
            request.headers[b'Authorization'] = auth


class UserAgentMiddleware:
    """This middleware allows spiders to override the user_agent"""
    def __init__(self, user_agent):
        self.user_agent = user_agent

    @classmethod
    def from_crawler(cls, crawler):
        o = cls(crawler.settings['USER_AGENT'])
        crawler.signals.connect(o.spider_opened, signal=signals.spider_opened)
        return o

    def spider_opened(self, spider):
        self.user_agent = getattr(spider, 'user_agent', self.user_agent)

    def process_request(self, request, spider):
        if self.user_agent:
            agent = np.random.choice(self.user_agent)
            request.headers.setdefault(b'User-Agent', agent)

    def process_exception(self, request, exception, spider):
        """
            If it returns None, Scrapy will continue processing this exception,
            executing any other process_exception() methods of installed middleware,
            until no middleware is left and the default exception handling kicks in.

            If it returns a Request object, the returned request is rescheduled to be downloaded in the future.
            This stops the execution of process_exception() methods of the middleware the same as returning a response would.
        """
        return request


class HttpProxyMiddleware:
    """This middleware allows spiders to override the user_agent"""
    def __init__(self, proxy_ip):
        self.proxy_ip = proxy_ip

    @classmethod
    def from_crawler(cls, crawler):
        o = cls(crawler.settings['USER_PROXY_IP'])
        crawler.signals.connect(o.spider_opened, signal=signals.spider_opened)
        return o

    def spider_opened(self, spider):
        self.proxy_ip = getattr(spider, 'USER_PROXY_IP', self.proxy_ip)

    def process_request(self, request, spider):
        proxy_entry = random.choice(self.proxy_ip)
        spider.logger.info(f"Using proxy: {proxy_entry}")
        if proxy_entry:
            # 格式支持：
            # - http://host:port
            # - http://user:pass@host:port
            if "@" in proxy_entry:
                creds, address = proxy_entry.split("@")
                user_pass = creds.split("://")[1]
                encoded_user_pass = base64.b64encode(user_pass.encode("utf-8")).decode("utf-8")
                request.headers['Proxy-Authorization'] = 'Basic ' + encoded_user_pass
                request.meta['proxy'] = "http://" + address
            else:
                request.meta['proxy'] = proxy_entry


class RedirectMiddleware:

    def process_response(self, request, response, spider):
        if response.status in getattr(spider, 'handle_httpstatus_list', []):
            return request
        return response


class CustomRetryMiddleware:

    # IOError is raised by the HttpCompression middleware when trying to
    # decompress an empty response
    EXCEPTIONS_TO_RETRY = (defer.TimeoutError, TimeoutError, DNSLookupError,
                           ConnectionRefusedError, ConnectionDone, ConnectError,
                           ConnectionLost, TCPTimedOutError, ResponseFailed,
                           IOError, TunnelError)

    def __init__(self, settings):
        if not settings.getbool('RETRY_ENABLED'):
            raise NotConfigured
        self.max_retry_times = settings.getint('RETRY_TIMES')
        self.retry_http_codes = set(int(x) for x in settings.getlist('RETRY_HTTP_CODES'))
        self.priority_adjust = settings.getint('RETRY_PRIORITY_ADJUST')

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.settings)

    def process_response(self, request, response, spider):
        if request.meta.get('dont_retry', False):
            return response
        if response.status in self.retry_http_codes:
            reason = response_status_message(response.status)
            return self._retry(request, reason, spider) or response
        return response

    def process_exception(self, request, exception, spider):
        if (
            isinstance(exception, self.EXCEPTIONS_TO_RETRY)
            and not request.meta.get('dont_retry', False)
        ):
            return self._retry(request, exception, spider)

    def _retry(self, request, reason, spider):
        max_retry_times = request.meta.get('max_retry_times', self.max_retry_times)
        priority_adjust = request.meta.get('priority_adjust', self.priority_adjust)
        return get_retry_request(
            request,
            reason=reason,
            spider=spider,
            max_retry_times=max_retry_times,
            priority_adjust=priority_adjust,
        )


# def get_retry_request(
#     request: Request,
#     *,
#     spider: Spider,
#     reason: Union[str, Exception] = 'unspecified',
#     max_retry_times: Optional[int] = None,
#     priority_adjust: Optional[int] = None,
#     logger: Logger = None,
#     stats_base_key: str = 'retry',
# ):
#     """
#     Returns a new :class:`~scrapy.Request` object to retry the specified
#     request, or ``None`` if retries of the specified request have been
#     exhausted.

#     For example, in a :class:`~scrapy.Spider` callback, you could use it as
#     follows::

#         def parse(self, response):
#             if not response.text:
#                 new_request_or_none = get_retry_request(
#                     response.request,
#                     spider=self,
#                     reason='empty',
#                 )
#                 return new_request_or_none

#     *spider* is the :class:`~scrapy.Spider` instance which is asking for the
#     retry request. It is used to access the :ref:`settings <topics-settings>`
#     and :ref:`stats <topics-stats>`, and to provide extra logging context (see
#     :func:`logging.debug`).

#     *reason* is a string or an :class:`Exception` object that indicates the
#     reason why the request needs to be retried. It is used to name retry stats.

#     *max_retry_times* is a number that determines the maximum number of times
#     that *request* can be retried. If not specified or ``None``, the number is
#     read from the :reqmeta:`max_retry_times` meta key of the request. If the
#     :reqmeta:`max_retry_times` meta key is not defined or ``None``, the number
#     is read from the :setting:`RETRY_TIMES` setting.

#     *priority_adjust* is a number that determines how the priority of the new
#     request changes in relation to *request*. If not specified, the number is
#     read from the :setting:`RETRY_PRIORITY_ADJUST` setting.

#     *logger* is the logging.Logger object to be used when logging messages

#     *stats_base_key* is a string to be used as the base key for the
#     retry-related job stats
#     """
#     settings = spider.crawler.settings
#     stats = spider.crawler.stats
#     retry_times = request.meta.get('retry_times', 0) + 1

#     max_retry_times = max_retry_times if max_retry_times else request.meta.get('max_retry_times', settings.getint('RETRY_TIMES'))
#     logger = logger if logger else spider.logger

#     if retry_times <= max_retry_times:
#         logger.debug(
#             "Retrying %(request)s (failed %(retry_times)d times): %(reason)s",
#             {'request': request, 'retry_times': retry_times, 'reason': reason},
#             extra={'spider': spider}
#         )
#         new_request = request.copy()
#         new_request.dont_filter = True
#         new_request.meta['retry_times'] = retry_times
#         new_request.meta['retry_delay'] = 2 ** retry_times  # exponential backoff

#         if priority_adjust is None:
#             priority_adjust = settings.getint('RETRY_PRIORITY_ADJUST')
#         new_request.priority = request.priority + priority_adjust

#         if callable(reason):
#             reason = reason()
#         if isinstance(reason, Exception):
#             reason = global_object_name(reason.__class__)

#         stats.inc_value(f'{stats_base_key}/count')
#         stats.inc_value(f'{stats_base_key}/reason_count/{reason}')
#         return new_request
#     else:
#         stats.inc_value(f'{stats_base_key}/max_reached')
#         logger.error(
#             "Gave up retrying %(request)s (failed %(retry_times)d times): "
#             "%(reason)s",
#             {'request': request, 'retry_times': retry_times, 'reason': reason},
#             extra={'spider': spider},
#         )
#         return None
