import asyncio
# ✅ 安装 AsyncioSelectorReactor 必须在任何 Twisted 导入之前
from twisted.internet import asyncioreactor
asyncioreactor.install() # not new_event_loop() / get_event_loop()

# default is twisted.internet.selectreactor.SelectReactor
from twisted.internet import reactor, defer, error
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
        print("Asset Spider Starting")
        yield runner.crawl(Stock) # Twisted Deferred

        print("Adjustment Spider Starting")
        yield runner.crawl(Adjustment)

        print("Rightment Spider Starting")
        yield runner.crawl(Rightment)
        
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
                print("Reactor was not running or already stopped.")


if __name__ == '__main__':

    load_dotenv()

    d = crawl()  # deferred to track spider
    d.addErrback(lambda f: f.printTraceback())
    reactor.run()
