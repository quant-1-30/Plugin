import asyncio
# ✅ 安装 AsyncioSelectorReactor 必须在任何 Twisted 导入之前
from twisted.internet import asyncioreactor
asyncioreactor.install() # not new_event_loop() / get_event_loop()

# default is twisted.internet.selectreactor.SelectReactor
from twisted.internet import reactor, defer
from scrapy.crawler import CrawlerRunner
# from scrapy.crawler import CrawlerProcess
from scrapy.utils.log import configure_logging
from scrapy.utils.project import get_project_settings
from dotenv import load_dotenv

from crawlers import *


# configure_logging()
configure_logging({'LOG_FORMAT': '%(levelname)s: %(message)s'})

# initialize project setting in crawlrunner
runner = CrawlerRunner(get_project_settings())


# run multiple spiders in sequence
@defer.inlineCallbacks
def crawl():
    try:
        # print("Stock Spider Starting")
        # yield runner.crawl(Stock) # Twisted Deferred

        # print("Adjustment Spider Starting")
        # yield runner.crawl(Adjustment)

        # print("Rightment Spider Starting")
        # yield runner.crawl(Rightment)
        
        print("Benchmark Spider Starting")
        yield runner.crawl(Benchmark) 

    except Exception as e:
        print(f"Spider Running Error: {e}")
    finally:
            print("🧹 All spiders finished. Ready to check reactor status...")
            if reactor.running:
                try:
                    reactor.stop()
                    print("✅ Reactor stopped cleanly.")
                except error.ReactorNotRunning:
                    pass
            else:
                print("ℹ️ Reactor was not running or already stopped.")


# @defer.inlineCallbacks
# def crawl():     # 同时启动所有爬虫
#     deferred_list = [
#         runner.crawl(Stock),
#         runner.crawl(Adjustment), 
#         runner.crawl(Rightment)
#     ]
    
#     yield defer.DeferredList(deferred_list)
#     print("所有爬虫并发执行完成")
#     reactor.stop()


# def crawl():
#     process = CrawlerProcess(get_project_settings())
    
#     process.crawl(Stock)
#     process.crawl(Adjustment) 
#     process.crawl(Rightment)
    
#     print("并发执行爬虫...")
#     process.start()  # 会自动并发执行所有爬虫
#     print("所有爬虫执行完成")


if __name__ == '__main__':

    load_dotenv()
    # 创建一个 deferred 对象来跟踪爬虫的完成
    d = crawl()
    # 添加错误处理
    d.addErrback(lambda f: f.printTraceback())
    # 运行 reactor
    reactor.run()
