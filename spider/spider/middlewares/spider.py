# Define here the models for your spider middleware
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/spider-middleware.html

import collections
import logging

from scrapy import signals
from scrapy.exceptions import IgnoreRequest, NotConfigured

logger = logging.getLogger(__name__)

__all__ = ['ErrorSpiderMiddleware', 'HttpErrorMiddleware']


class HttpError(IgnoreRequest):
    """A non-200 response was filtered"""

    def __init__(self, response, *args, **kwargs):
        self.response = response
        super().__init__(*args, **kwargs)


class SpiderSpiderMiddleware:
    @classmethod
    def from_crawler(cls, crawler):
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_spider_input(self, response, spider):
        return None

    async def process_spider_output(self, response, result, spider):
        # result async generator
        if isinstance(result, collections.AsyncIterable):
            async for r in result:
                yield r
        else:
            for r in result:
                yield r

    def process_spider_exception(self, response, exception, spider):
        return None

    def process_start_requests(self, start_requests, spider):
        for r in start_requests:
            yield r

    def spider_opened(self, spider):
        spider.logger.info('Spider opened: %s' % spider.name)


class ErrorSpiderMiddleware:
    """record status not abandon item/request"""

    handle_httpstatus_list = [456, 500, 502, 503, 504, 522, 524, 408, 429]

    async def process_spider_output(self, response, result, spider):
        if response.status in self.handle_httpstatus_list:
            spider.logger.error(
                f"Received error status {response.status} for {response.url}"
            )
        # item/request
        if isinstance(result, collections.abc.AsyncIterable):
            async for item in result:
                yield item
        else:
            for item in result:
                yield item


class HttpErrorMiddleware:

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.settings)

    def __init__(self, settings):
        self.handle_httpstatus_all = settings.getbool('HTTPERROR_ALLOW_ALL')
        self.handle_httpstatus_list = settings.getlist('HTTPERROR_ALLOWED_CODES')

    def process_spider_input(self, response, spider):
        if 200 <= response.status < 300:  # common case
            return
        meta = response.meta
        if meta.get('handle_httpstatus_all', False):
            return
        if 'handle_httpstatus_list' in meta:
            allowed_statuses = meta['handle_httpstatus_list']
        elif self.handle_httpstatus_all:
            return
        else:
            allowed_statuses = getattr(spider, 'handle_httpstatus_list', self.handle_httpstatus_list)
        if response.status in allowed_statuses:
            return
        raise HttpError(response, 'Ignoring non-200 response')

    def process_spider_exception(self, response, exception, spider):
        if isinstance(exception, HttpError):
            spider.crawler.stats.inc_value('httperror/response_ignored_count')
            spider.crawler.stats.inc_value(
                f'httperror/response_ignored_status_count/{response.status}'
            )
            logger.info(
                "Ignoring response %(response)r: HTTP status code is not handled or not allowed",
                {'response': response}, extra={'spider': spider},
            )
            return []
        return None