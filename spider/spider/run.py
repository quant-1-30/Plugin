#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Mar 12 15:37:47 2019

@author: python
"""
import asyncio
# ✅ 安装 AsyncioSelectorReactor 必须在任何 Twisted 导入之前
from twisted.internet import asyncioreactor
asyncioreactor.install() # not new_event_loop() / get_event_loop()

from dotenv import load_dotenv
load_dotenv()

# default is twisted.internet.selectreactor.SelectReactor
from twisted.internet import reactor, defer, error
from scrapy.crawler import CrawlerRunner
# from scrapy.crawler import CrawlerProcess
from scrapy.utils.log import configure_logging
from scrapy.utils.project import get_project_settings

from crawlers import *
from utils.operator import async_ops, _get_reactor_loop


# configure_logging()
configure_logging({'LOG_FORMAT': '%(levelname)s: %(message)s'})

# initialize project setting in crawlrunner
runner = CrawlerRunner(get_project_settings())


# run multiple spiders in sequence
@defer.inlineCallbacks
def crawl():
    try:
        for label, spider_cls in (
            ("Asset", Stock),
            ("Adjustment", Adjustment),
            ("Rightment", Rightment),
            ("Benchmark", Benchmark),
        ):
            try:
                print(f"{label} Spider Starting")
                yield runner.crawl(spider_cls)
            except Exception as e:
                print(f"{label} Spider Running Error: {e}")
    finally:
        try:
            loop = _get_reactor_loop()
            cleanup_future = asyncio.run_coroutine_threadsafe(async_ops.cleanup(), loop)
            yield defer.Deferred.fromFuture(cleanup_future)
        except Exception as e:
            print(f"AsyncOps cleanup warning: {e}")

        print("🧹 All spiders finished. Ready to check reactor status...")
        if reactor.running:
            try:
                reactor.stop()
                print("✅ Reactor stopped cleanly.")
            except error.ReactorNotRunning:
                pass
        else:
            print("Reactor was not running or already stopped.")


if __name__ == '__main__':

    d = crawl()  # deferred to track spider
    d.addErrback(lambda f: f.printTraceback())
    reactor.run()
