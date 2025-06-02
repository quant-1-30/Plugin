# # /usr/bin/env python3
# # -*- coding : utf-8 -*-
# """
# Created on Tue Mar 12 15:37:47 2019

# @author: python
# """
# # ✅ 安装 AsyncioSelectorReactor 必须在任何 Twisted 导入之前
# from twisted.internet import asyncioreactor
# asyncioreactor.install()

# # default is twisted.internet.selectreactor.SelectReactor
# from twisted.internet import reactor, defer
# from scrapy.crawler import CrawlerRunner
# from scrapy.utils.log import configure_logging
# from scrapy.utils.project import get_project_settings
# from tutorial.spiders import *


# # configure_logging()
# configure_logging({'LOG_FORMAT': '%(levelname)s: %(message)s'})

# # initialize project setting in crawlrunner
# # runner = CrawlerRunner()
# runner = CrawlerRunner(get_project_settings())


# # run multiple spiders
# @defer.inlineCallbacks
# def crawl():
#     yield runner.crawl(Stock)
#     # yield runner.crawl(Adjustment)
#     # yield runner.crawl(Rightment)
#     # yield runner.crawl(Kline)
#     reactor.stop()


# if __name__ == '__main__':
#     # 创建一个 deferred 对象来跟踪爬虫的完成
#     d = crawl()
#     # 添加错误处理
#     d.addErrback(lambda f: f.printTraceback())
#     # 运行 reactor
#     reactor.run()


import asyncio
from scrapy.utils.project import get_project_settings
from scrapy.crawler import CrawlerProcess
from scrapy.utils.log import configure_logging
from tutorial.spiders import Stock

from twisted.internet import asyncioreactor
asyncioreactor.install()

if __name__ == "__main__":
    # 配置日志
    configure_logging({'LOG_FORMAT': '%(levelname)s: %(message)s'})
    
    # 使用 CrawlerProcess
    process = CrawlerProcess(get_project_settings())
    
    # 添加错误处理
    def handle_error(failure):
        print(f"Error occurred: {failure}")
        return failure
    
    # 运行爬虫
    deferred = process.crawl(Stock)
    deferred.addErrback(handle_error)
    
    # 启动爬虫
    process.start() 