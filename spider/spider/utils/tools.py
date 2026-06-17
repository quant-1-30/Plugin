# !/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Mar 12 15:37:47 2019

@author: python
"""
from datetime import datetime
from logging import Logger
from typing import Optional, Union, Dict

from scrapy.http.request import Request
from scrapy.spiders import Spider
from scrapy.utils.python import global_object_name


def coerce_to_uint32(a, scaling_factor):
    """
    Returns a copy of the array as uint32, applying a scaling factor to
    maintain precision if supplied.
    """
    return (a * scaling_factor).round().astype('uint32')


def quarter_date(sdate, fmt="%Y-%m-%d"):
    # 0331 / 0630 / 0930 / 1231
    sdate = datetime.strptime(str(sdate), fmt)
    edate = datetime.now()
    dates = []
    current_year = sdate.year
    end_year = edate.year
    
    while current_year <= end_year:
        march_date = datetime(current_year, 3, 31)
        if sdate <= march_date <= edate:  
            dates.append(march_date.strftime(fmt))

        june_date = datetime(current_year, 6, 30)
        if sdate <= june_date <= edate:  
            dates.append(june_date.strftime(fmt))
        
        sept_date = datetime(current_year, 9, 30)
        if sdate <= sept_date <= edate:  
            dates.append(sept_date.strftime(fmt))
        
        dec_date = datetime(current_year, 12, 31)
        if sdate <= dec_date <= edate:  
            dates.append(dec_date.strftime(fmt))
        
        current_year += 1
    return dates


def get_adjacent_quarter(adj_ex_date: Dict[str, int], offset: int=1):
        """
            03-31 / 06-30 / 09-30 / 12-31
        """
        if not adj_ex_date:
            return '1990-01-01'

        max_ex_date = max(adj_ex_date.values())
        try:
            max_date = datetime.strptime(str(max_ex_date), '%Y%m%d')
            near_date = max_date.replace(year=max_date.year - offset)
        except Exception as e:
            return '1990-01-01'

        year = near_date.year
        if near_date >= datetime(year, 12, 31):
            start_date_obj = datetime(year, 12, 31)
        elif near_date >= datetime(year, 9, 30):
            start_date_obj = datetime(year, 9, 30)
        elif near_date >= datetime(year, 6, 30):
            start_date_obj = datetime(year, 6, 30)
        elif near_date >= datetime(year, 3, 31):
            start_date_obj = datetime(year, 3, 31)
        else:
            start_date_obj = datetime(year - 1, 12, 31)

        return start_date_obj.strftime('%Y-%m-%d')


def get_retry_request(
    request: Request,
    *,
    spider: Spider,
    reason: Union[str, Exception] = 'unspecified',
    max_retry_times: Optional[int] = None,
    priority_adjust: Optional[int] = None,
    logger: Logger = None,
    stats_base_key: str = 'retry',
):
    """
    Returns a new :class:`~scrapy.Request` object to retry the specified
    request, or ``None`` if retries of the specified request have been
    exhausted.

    For example, in a :class:`~scrapy.Spider` callback, you could use it as
    follows::

        def parse(self, response):
            if not response.text:
                new_request_or_none = get_retry_request(
                    response.request,
                    spider=self,
                    reason='empty',
                )
                return new_request_or_none

    *spider* is the :class:`~scrapy.Spider` instance which is asking for the
    retry request. It is used to access the :ref:`settings <topics-settings>`
    and :ref:`stats <topics-stats>`, and to provide extra logging context (see
    :func:`logging.debug`).

    *reason* is a string or an :class:`Exception` object that indicates the
    reason why the request needs to be retried. It is used to name retry stats.

    *max_retry_times* is a number that determines the maximum number of times
    that *request* can be retried. If not specified or ``None``, the number is
    read from the :reqmeta:`max_retry_times` meta key of the request. If the
    :reqmeta:`max_retry_times` meta key is not defined or ``None``, the number
    is read from the :setting:`RETRY_TIMES` setting.

    *priority_adjust* is a number that determines how the priority of the new
    request changes in relation to *request*. If not specified, the number is
    read from the :setting:`RETRY_PRIORITY_ADJUST` setting.

    *logger* is the logging.Logger object to be used when logging messages

    *stats_base_key* is a string to be used as the base key for the
    retry-related job stats
    """
    settings = spider.crawler.settings
    stats = spider.crawler.stats
    retry_times = request.meta.get('retry_times', 0) + 1

    max_retry_times = max_retry_times if max_retry_times else request.meta.get('max_retry_times', settings.getint('RETRY_TIMES'))
    logger = logger if logger else spider.logger

    if retry_times <= max_retry_times:
        logger.debug(
            "Retrying %(request)s (failed %(retry_times)d times): %(reason)s",
            {'request': request, 'retry_times': retry_times, 'reason': reason},
            extra={'spider': spider}
        )
        new_request = request.copy()
        new_request.dont_filter = True
        new_request.meta['retry_times'] = retry_times
        new_request.meta['retry_delay'] = 2 ** retry_times  # exponential backoff

        if priority_adjust is None:
            priority_adjust = settings.getint('RETRY_PRIORITY_ADJUST')
        new_request.priority = request.priority + priority_adjust

        if callable(reason):
            reason = reason()
        if isinstance(reason, Exception):
            reason = global_object_name(reason.__class__)

        stats.inc_value(f'{stats_base_key}/count')
        stats.inc_value(f'{stats_base_key}/reason_count/{reason}')
        return new_request
    else:
        stats.inc_value(f'{stats_base_key}/max_reached')
        logger.error(
            "Gave up retrying %(request)s (failed %(retry_times)d times): "
            "%(reason)s",
            {'request': request, 'retry_times': retry_times, 'reason': reason},
            extra={'spider': spider},
        )
        return None