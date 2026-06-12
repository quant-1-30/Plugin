# # spider/encoders.py
# import json
# from scrapy.exporters import JsonLinesItemExporter

# from spider.encoder import CustomFeedJsonEncoder


# class SafeJsonLinesExporter(JsonLinesItemExporter):
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.encoder = CustomFeedJsonEncoder()
