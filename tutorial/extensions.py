# /usr/bin/env python3
# -*- coding : utf-8 -*-
"""
Created on Tue Mar 12 15:37:47 2019

@author: python
"""

# extensions
import logging
from datetime import datetime
from scrapy import signals
from scrapy.mail import MailSender
from scrapy.exceptions import NotConfigured

logger = logging.getLogger(__name__)


class CoreStats:

    def __init__(self, stats):
        self.stats = stats
        self.start_time = None

    @classmethod
    def from_crawler(cls, crawler):
        o = cls(crawler.stats)
        crawler.signals.connect(o.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(o.spider_closed, signal=signals.spider_closed)
        crawler.signals.connect(o.item_scraped, signal=signals.item_scraped)
        crawler.signals.connect(o.item_dropped, signal=signals.item_dropped)
        crawler.signals.connect(o.response_received, signal=signals.response_received)
        return o

    def spider_opened(self, spider):
        self.start_time = datetime.utcnow()
        self.stats.set_value('start_time', self.start_time, spider=spider)

    def spider_closed(self, spider, reason):
        finish_time = datetime.utcnow()
        elapsed_time = finish_time - self.start_time
        elapsed_time_seconds = elapsed_time.total_seconds()
        self.stats.set_value('elapsed_time_seconds', elapsed_time_seconds, spider=spider)
        self.stats.set_value('finish_time', finish_time, spider=spider)
        self.stats.set_value('finish_reason', reason, spider=spider)

    def item_scraped(self, item, spider):
        self.stats.inc_value('item_scraped_count', spider=spider)

    def response_received(self, spider):
        self.stats.inc_value('response_received_count', spider=spider)

    def item_dropped(self, item, spider, exception):
        reason = exception.__class__.__name__
        self.stats.inc_value('item_dropped_count', spider=spider)
        self.stats.inc_value(f'item_dropped_reasons_count/{reason}', spider=spider)


class StatsMailer:

    def __init__(self, stats, recipients, mail):
        self.stats = stats
        self.recipients = recipients
        self.mail = mail

    @classmethod
    def from_crawler(cls, crawler):
        recipients = crawler.settings.getlist("STATSMAILER_RCPTS")
        if not recipients:
            raise NotConfigured
        mail = MailSender.from_settings(crawler.settings)
        o = cls(crawler.stats, recipients, mail)
        crawler.signals.connect(o.spider_closed, signal=signals.spider_closed)
        return o

    def spider_closed(self, spider):
        spider_stats = self.stats.get_stats(spider)
        body = "Global stats\n\n"
        body += "\n".join(f"{k:<50} : {v}" for k, v in self.stats.get_stats().items())
        body += f"\n\n{spider.name} stats\n\n"
        body += "\n".join(f"{k:<50} : {v}" for k, v in spider_stats.items())
        return self.mail.send(self.recipients, f"Scrapy stats for: {spider.name}", body)
