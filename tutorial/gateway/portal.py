# !/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Mar 12 15:37:47 2019

@author: python
"""


class BarReader(object):

    def load_assets(self):
        pass

    def load_raw_kline(self):
        pass


class McapReader(BarReader):

    def retrieve_ownership(self):
        pass

    def load_mcap(self):
        pass


class Adjustments(BarReader):

    def retrieve_dividends(self):
        pass

    def retrieve_rights(self):
        pass


class Ext(BarReader):

    def load_specific_kline(self):
        pass


class DataPortal(McapReader, Adjustments, Ext):

    pass

