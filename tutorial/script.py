# /usr/bin/env python3
# -*- coding : utf-8 -*-
"""
Created on Tue Mar 12 15:37:47 2019

@author: python
"""
from twisted.internet import reactor, defer
from scrapy.crawler import CrawlerRunner
from scrapy.utils.log import configure_logging
from scrapy.utils.project import get_project_settings
from spiders import Stock, Dual, Bond, Fund, Index, Basics

# run spiders
# from scrapy.crawler import CrawlerProcess
# from scrapy.utils.project import get_project_settings
#
# process = CrawlerProcess(get_project_settings())
#
# # 'followall' is the name of one of the spiders of the project.
# process.crawl('followall', domain='scrapy.org')
# process.start() # the script will block here until the crawling is finished

# It’s recommended you use CrawlerRunner instead of CrawlerProcess
# if your application is already using Twisted and you want to run Scrapy in the same reactor.

# from twisted.internet import reactor
# import scrapy
# from scrapy.crawler import CrawlerRunner
# from scrapy.utils.log import configure_logging
#
# class MySpider(scrapy.Spider):
#     # Your spider definition
#     ...
#
# configure_logging({'LOG_FORMAT': '%(levelname)s: %(message)s'})
# runner = CrawlerRunner()
# d = runner.crawl(MySpider)

# runner = CrawlerRunner()
# runner.crawl(MySpider1)
# runner.crawl(MySpider2)
# d = runner.join()

# d.addBoth(lambda _: reactor.stop())
# reactor.run() # the script will block here until the crawling is finished

configure_logging()
# initialize project setting in crawlrunner
runner = CrawlerRunner(get_project_settings())

# run multiple spiders
@defer.inlineCallbacks
def crawl():
    yield runner.crawl(Stock)
    yield runner.crawl(Dual)
    yield runner.crawl(Fund)
    yield runner.crawl(Bond)
    yield runner.crawl(Index)
    yield runner.crawl(Basics)
    reactor.stop()


if __name__ == '__main__':

    crawl()
    # the script will block here until the last crawl call is finished
    reactor.run()
