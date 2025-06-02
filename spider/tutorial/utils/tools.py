# !/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Mar 12 15:37:47 2019

@author: python
"""
import re
from urllib.parse import urlencode, quote
from tutorial.settings import META_URLS, Params


def params2url(sid, dual=False):
    if dual:
        prefix = '116.' + sid
    else:
        pattern = '(^6|5|11|000)[0-9]{4,5}$'
        match = re.match(pattern, sid)
        prefix = '1.' + sid if match else '0.' + sid
    # update sid
    p = Params.copy()
    p.update({'secid': prefix})
    url = META_URLS['kline'] + urlencode(p, quote_via=quote)
    return url

def coerce_to_uint32(a, scaling_factor):
    """
    Returns a copy of the array as uint32, applying a scaling factor to
    maintain precision if supplied.
    """
    return (a * scaling_factor).round().astype('uint32')

