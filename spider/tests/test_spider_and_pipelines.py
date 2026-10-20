#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Mar 12 15:37:47 2019

@author: python
"""
import asyncio
import json
import logging
import os
import tempfile
import unittest

import pandas as pd
from scrapy.exceptions import CloseSpider, DropItem
from scrapy.http import Request, TextResponse

from crawlers.adj import Adjustment as AdjustmentSpider
from crawlers.asset import Stock as StockSpider
from crawlers.benchmark import Benchmark as BenchmarkSpider
from crawlers.rgt import Rightment as RightmentSpider
from pipelines.pipelines import (
    Adjustment as AdjustmentPipeline,
    Asset as AssetPipeline,
    AsyncDb,
    JsonlFeed,
    ParquetWriter,
    Rightment as RightmentPipeline,
    namedData,
)
from utils.tools import (
    encode_sid,
    get_adjacent_quarter,
    is_valid_ashare_sid,
    parse_datetime_to_int,
)


async def _collect_async_gen(agen):
    results = []
    async for item in agen:
        results.append(item)
    return results


class TestToolsAndPipelines(unittest.TestCase):

    def setUp(self):
        os.environ.setdefault("ASSET_URL", "https://push2.eastmoney.com/api/qt/clist/get?")
        os.environ.setdefault("ADJ_URL", "https://datacenter-web.eastmoney.com/api/data/v1/get?")
        os.environ.setdefault("RGT_URL", "https://datacenter-web.eastmoney.com/api/data/v1/get?")
        os.environ.setdefault("INDEX_URL", "https://push2his.eastmoney.com/api/qt/stock/trends2/get?")
        os.environ.setdefault("INDEX", "1.000001")

    def test_tools_helpers(self):
        self.assertTrue(is_valid_ashare_sid("600000.SH"))
        self.assertTrue(is_valid_ashare_sid("688001.SH"))
        self.assertTrue(is_valid_ashare_sid("300001.SZ"))
        self.assertTrue(is_valid_ashare_sid("002001.SZ"))
        self.assertFalse(is_valid_ashare_sid("920005.BJ"))
        self.assertFalse(is_valid_ashare_sid("200001.SZ"))
        self.assertFalse(is_valid_ashare_sid("399001.SZ"))
        self.assertEqual(encode_sid("688001.SH"), b"688001")
        self.assertEqual(parse_datetime_to_int("2026-06-30 00:00:00"), 20260630)
        self.assertEqual(parse_datetime_to_int(None), 0)
        self.assertEqual(get_adjacent_quarter({"a": 20240229}, offset=1), "2022-12-31")

    def test_asset_pipeline(self):
        spider = StockSpider()
        spider.asset_latest_date = 20260101
        pipe = AssetPipeline()
        pipe.logger = logging.getLogger("test_asset")

        valid_item = {"sid": ["688001"], "name": ["华兴源创"], "first_trading": ["20260501"]}
        out = pipe.process_item(valid_item, spider)
        self.assertEqual(out["sid"], b"688001")
        self.assertEqual(out["first_trading"], 20260501)
        self.assertEqual(out["delist"], 0)

        with self.assertRaises(DropItem):
            pipe.process_item({"sid": ["688001"], "name": ["华兴源创"], "first_trading": ["-"]}, spider)

        with self.assertRaises(DropItem):
            pipe.process_item({"sid": ["688001"], "name": ["华兴源创"], "first_trading": ["20250101"]}, spider)

    def test_adjustment_and_rightment_pipeline_dedup_and_order(self):
        spider = AdjustmentSpider()
        spider.adj_ex_date = {b"688001": 20250101}
        pipe = AdjustmentPipeline()
        pipe.logger = logging.getLogger("test_adj")

        # Descending arrival: newer record arrives first, older (but > watermark) arrives second
        newer = {
            "sid": ["688001.SH"],
            "report_date": ["2025-12-31 00:00:00"],
            "register_date": ["2026-06-10 00:00:00"],
            "ex_date": ["2026-06-11 00:00:00"],
            "bonus": [3.0],
        }
        older_but_valid = {
            "sid": ["688001.SH"],
            "report_date": ["2025-06-30 00:00:00"],
            "register_date": ["2025-10-10 00:00:00"],
            "ex_date": ["2025-10-11 00:00:00"],
            "bonus": [1.5],
        }
        out1 = pipe.process_item(newer, spider)
        out2 = pipe.process_item(older_but_valid, spider)
        self.assertEqual(out1["ex_date"], 20260611)
        self.assertEqual(out1["bonus_share"], 0)
        self.assertEqual(out2["ex_date"], 20251011)

        # Duplicate record in same run should be dropped
        with self.assertRaises(DropItem):
            pipe.process_item(newer, spider)

        # L6: Late-announced historical dividend (ex_date < max_ex_date, but not in adj_known_keys)
        spider_with_known = AdjustmentSpider()
        spider_with_known.preload([(b"688001", 20260915)])
        pipe2 = AdjustmentPipeline()
        pipe2.logger = logging.getLogger("test_adj2")
        late_dividend = {
            "sid": ["688001.SH"],
            "report_date": ["2025-12-31 00:00:00"],
            "register_date": ["2026-05-29 00:00:00"],
            "ex_date": ["2026-06-01 00:00:00"],
            "bonus": [2.0],
        }
        late_out = pipe2.process_item(late_dividend, spider_with_known)
        self.assertEqual(late_out["ex_date"], 20260601)

        # RightmentPipeline deduplicates by (sid, report_date)
        rgt_spider = RightmentSpider()
        rgt_spider.rgt_ex_date = {b"300176": 20250101}
        rgt_pipe = RightmentPipeline()
        rgt_pipe.logger = logging.getLogger("test_rgt")
        rgt_item = {
            "sid": ["300176.SZ"],
            "report_date": ["2026-08-10 00:00:00"],
            "register_date": ["2026-08-12 00:00:00"],
            "ex_date": ["2026-08-21 00:00:00"],
            "ratio": [4],
            "price": [3.36],
        }
        rgt_out = rgt_pipe.process_item(rgt_item, rgt_spider)
        self.assertEqual(rgt_out["sid"], b"300176")
        self.assertEqual(rgt_out["report_date"], 20260810)
        with self.assertRaises(DropItem):
            rgt_pipe.process_item(rgt_item, rgt_spider)

    def test_stock_parse_early_stop(self):
        spider = StockSpider()
        spider.asset_latest_date = 20260501
        req = Request(
            "https://push2.eastmoney.com/api/qt/clist/get?pn=1",
            meta={"page": 1, "params": {"pn": 1}, "retry_times": 0},
        )
        payload = {
            "data": {
                "diff": [
                    {"f12": "600000", "f14": "浦发银行", "f26": 20260101},
                ]
            }
        }
        resp = TextResponse(url=req.url, request=req, body=json.dumps(payload).encode("utf-8"))
        outputs = asyncio.run(_collect_async_gen(spider.parse(resp)))
        # Should yield 1 AssetItem and stop pagination (no next page Request)
        self.assertEqual(len(outputs), 1)
        self.assertNotIsInstance(outputs[0], Request)

    def test_parquet_writer(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            writer = ParquetWriter(dataset_root=tmpdir)
            writer.logger = logging.getLogger("test_parquet")
            spider = BenchmarkSpider()
            writer.open_spider(spider)
            writer.process_item(
                {
                    "sid": ["000001"],
                    "tick": ["2026-06-18 09:30"],
                    "open": ["3000.0"],
                    "close": ["3005.0"],
                    "high": ["3006.0"],
                    "low": ["2999.0"],
                    "volume": ["1000"],
                    "amount": ["500000"],
                },
                spider,
            )
            writer.close_spider(spider)
            # Second write on same day with new tick to verify incremental merge
            writer.process_item(
                {
                    "sid": ["000001"],
                    "tick": ["2026-06-18 09:31"],
                    "open": ["3005.0"],
                    "close": ["3010.0"],
                    "high": ["3012.0"],
                    "low": ["3004.0"],
                    "volume": ["1200"],
                    "amount": ["600000"],
                },
                spider,
            )
            writer.close_spider(spider)
            parquet_files = []
            for root, _, files in os.walk(tmpdir):
                for f in files:
                    if f.endswith(".parquet"):
                        parquet_files.append(os.path.join(root, f))
            self.assertEqual(len(parquet_files), 1)
            df = pd.read_parquet(parquet_files[0])
            self.assertEqual(len(df), 2)


    def test_adjustment_parse(self):
        adj_spider = AdjustmentSpider()
        adj_spider.preload([(b"688001", 20260611)])
        inc_reqs = list(adj_spider.start_requests())
        self.assertEqual(len(inc_reqs), 1)
        self.assertIn("EX_DIVIDEND_DATE>='2026-03-31'", inc_reqs[0].meta["params"]["filter"])

        adj_req = Request(
            "https://datacenter-web.eastmoney.com/api/data/v1/get?pageNumber=1",
            meta={"params": {"pageNumber": 1, "filter": "(EX_DIVIDEND_DATE>='2026-03-31')"}, "report_date": ">=2026-03-31"},
        )
        adj_payload = {
            "result": {
                "pages": 1,
                "data": [
                    {
                        "SECUCODE": "688001.SH",
                        "REPORT_DATE": "2026-06-30 00:00:00",
                        "EQUITY_RECORD_DATE": "2026-09-10 00:00:00",
                        "EX_DIVIDEND_DATE": "2026-09-11 00:00:00",
                        "BONUS_RATIO": None,
                        "IT_RATIO": None,
                        "PRETAX_BONUS_RMB": 2.5,
                    }
                ],
            }
        }
        adj_resp = TextResponse(url=adj_req.url, request=adj_req, body=json.dumps(adj_payload).encode("utf-8"))
        adj_items = asyncio.run(_collect_async_gen(adj_spider.parse(adj_resp)))
        self.assertEqual(len(adj_items), 1)
        self.assertEqual(adj_items[0]["bonus_share"], [0])
        self.assertEqual(adj_items[0]["bonus"], [2.5])

    def test_rightment_parse_and_server_filter(self):
        rgt_spider = RightmentSpider()
        rgt_spider.preload([(b"300176", 20260821)])
        start_reqs = list(rgt_spider.start_requests())
        self.assertEqual(len(start_reqs), 1)
        self.assertIn("EQUITY_RECORD_DATE", start_reqs[0].meta["params"]["filter"])

        rgt_req = Request(
            "https://datacenter-web.eastmoney.com/api/data/v1/get?pageNumber=1",
            meta={"params": {"pageNumber": 1}},
        )
        rgt_payload = {
            "result": {
                "pages": 1,
                "data": [
                    {
                        "SECUCODE": "300176.SZ",
                        "FIRST_NOTICE_DATE": "2024-01-10 00:00:00",
                        "EQUITY_RECORD_DATE": "2024-01-12 00:00:00",
                        "EX_DIVIDEND_DATE": "2024-01-15 00:00:00",
                        "PLACING_RATIO": 3,
                        "ISSUE_PRICE": 5.0,
                    }
                ],
            }
        }
        rgt_resp = TextResponse(url=rgt_req.url, request=rgt_req, body=json.dumps(rgt_payload).encode("utf-8"))
        rgt_items = asyncio.run(_collect_async_gen(rgt_spider.parse(rgt_resp)))
        self.assertEqual(len(rgt_items), 1)
        self.assertNotIsInstance(rgt_items[0], Request)

    def test_benchmark_parse(self):
        bm_spider = BenchmarkSpider()
        bm_req = Request("https://push2his.eastmoney.com/api/qt/stock/trends2/get?secid=1.000001")
        bm_payload = {
            "data": {
                "code": "000001",
                "trends": ["2026-06-18 09:30,3000.0,3005.0,3006.0,2999.0,1000,500000"],
            }
        }
        bm_resp = TextResponse(url=bm_req.url, request=bm_req, body=json.dumps(bm_payload).encode("utf-8"))
        bm_items = asyncio.run(_collect_async_gen(bm_spider.parse(bm_resp)))
        self.assertEqual(len(bm_items), 1)
        self.assertEqual(bm_items[0]["sid"], ["000001"])

    def test_asyncdb_flush_batch_mock(self):
        inserted = []

        class MockOps:
            async def on_insert_many(self, table, rows):
                inserted.append((table, rows))

        db_pipe = AsyncDb(batch_size=2)
        batches = [
            namedData("asset", {"sid": b"600000", "name": b"PF", "first_trading": 19991110, "delist": 0}),
            namedData("asset", {"sid": b"000001", "name": b"PA", "first_trading": 19910403, "delist": 0}),
        ]
        asyncio.run(db_pipe._flush_batch(batches, MockOps()))
        self.assertEqual(len(inserted), 1)
        self.assertEqual(inserted[0][0], "asset")
        self.assertEqual(len(inserted[0][1]), 2)

    def test_watermark_failure_raises_closespider(self):
        spider = StockSpider()
        closed_reasons = []

        class DummyEngine:
            def close_spider(self, sp, reason):
                closed_reasons.append((sp, reason))

        class DummyCrawler:
            engine = DummyEngine()

        spider.crawler = DummyCrawler()

        class DummyFailure:
            value = RuntimeError("db connection refused")

        spider.on_watermark_error(DummyFailure())
        self.assertEqual(closed_reasons, [(spider, "watermark_unavailable")])
        with self.assertRaises(CloseSpider):
            list(spider.start_requests())

    def test_benchmark_filters_invalid_index_and_sets_ndays_5(self):
        os.environ["INDEX"] = "1.000001,1.000688,0,"
        bm_spider = BenchmarkSpider()
        reqs = list(bm_spider.start_requests())
        self.assertEqual(len(reqs), 2)
        self.assertIn("ndays=5", reqs[0].url)


if __name__ == "__main__":
    unittest.main()
