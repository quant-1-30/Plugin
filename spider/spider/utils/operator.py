# !/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import asyncio
from twisted.internet import defer
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from contextlib import asynccontextmanager

__all__ = ["async_ops", "_get_reactor_loop"]


def _get_reactor_loop():
    """AsyncioSelectorReactor avoid asyncio.get_event_loop ---> Python 3.12+ 会触发
    DeprecationWarning/RuntimeError
    """
    try:
        from twisted.internet import reactor
        if hasattr(reactor, "_asyncioEventloop"):
            return reactor._asyncioEventloop
    except Exception:
        pass
    try:
        return asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop


class AsyncOps(object):
    """异步数据库访问封装。

    通过 SQLAlchemy AsyncEngine + AsyncSession 操作 PostgreSQL，
    并将协程桥接到 Twisted Deferred 以便 Scrapy 使用。
    """

    params = ()

    def __init__(self):
        self._initialized = False
        self.engine = None
        self._session_factory = None
        # 延迟获取事件循环，避免模块导入时出错
        self._loop = None

    def _ensure_loop(self):
        if self._loop is None:
            self._loop = _get_reactor_loop()
        return self._loop

    async def __aenter__(self):
        await self._ensure_initialized()
        return self

    async def _async_initialize(self):
        """Async initialization method"""
        if self._initialized:
            return
        await self._build_engine()
        self._initialized = True

    async def _ensure_initialized(self):
        """Helper method to ensure initialization"""
        if not self._initialized:
            await self._async_initialize()

    async def _build_engine(self):
        """构建异步引擎与会话工厂（仅构建一次，避免每次重建 sessionmaker）。"""
        url = (
            f'postgresql+{os.getenv("PGENGINE")}://{os.getenv("PGUSER")}:'
            f'{os.getenv("PGPWD")}@{os.getenv("PGHOST")}:'
            f'{os.getenv("PGPORT")}/{os.getenv("PGDB")}'
        )
        engine = create_async_engine(
            url,
            pool_size=int(os.getenv("PGPOOLSIZE", 20)),
            pool_timeout=int(os.getenv("PGTIMEOUT", 30)),
            max_overflow=int(os.getenv("PGMAXOVERFLOW", 10)),
            pool_recycle=int(os.getenv("PGPOOLRECYCLE", 3600)),
            pool_pre_ping=bool(int(os.getenv("PGPREPING", 1))),
            echo=bool(int(os.getenv("PGECHO", 0))),
        ).execution_options(compiled_cache={})

        self.engine = engine
        # 缓存 sessionmaker，避免每次 get_db 都重新创建
        self._session_factory = sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    @asynccontextmanager
    async def get_db(self):
        """获取一个异步会话，退出时自动关闭；发生异常自动回滚。"""
        await self._ensure_initialized()
        session = self._session_factory()
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    @staticmethod
    def filter_valid_keys(base_obj, insert):
        valid_keys = [column.name for column in base_obj.__table__.columns]
        return {key: value for key, value in insert.items() if key in valid_keys}

    async def reset_sequence(self, table_name):
        """重置表的自增序列"""
        async with self.get_db() as session:
            async with session.begin():
                result = await session.execute(
                    text(f"SELECT pg_get_serial_sequence('{table_name}', 'id')")
                )
                sequence_name = result.scalar()
                if sequence_name:
                    await session.execute(
                        text(f"ALTER SEQUENCE {sequence_name} RESTART WITH 1")
                    )

    @defer.inlineCallbacks
    def on_query(self, query: str):
        """将异步查询提交到 reactor 事件循环，并桥接为 Twisted Deferred。"""
        try:
            loop = self._ensure_loop()
            future = asyncio.run_coroutine_threadsafe(self._async_query(query), loop)
            results = yield defer.Deferred.fromFuture(future)
            defer.returnValue(results)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"on_query error: {e}", exc_info=True)
            defer.returnValue([])

    async def _async_query(self, query: str):
        async with self.get_db() as session:
            if isinstance(query, str):
                query_obj = text(query)
            else:
                query_obj = query
            stream = await session.stream(query_obj)
            results = []
            async for row in stream:
                results.append(row)
            return results

    async def on_insert(self, sql: str, param: dict):
        """插入单条记录。session.begin() 上下文会自动提交，无需手动 commit。"""
        async with self.get_db() as session:
            async with session.begin():
                await session.execute(sql, param)

    async def on_insert_many(self, table: str, rows: list):
        """批量插入。rows 为 dict 列表，使用 executemany 语义。"""
        if not rows:
            return
        cols = list(rows[0].keys())
        columns = ", ".join(cols)
        values = ", ".join([f":{k}" for k in cols])
        sql = text(f"INSERT INTO {table} ({columns}) VALUES ({values})")
        async with self.get_db() as session:
            async with session.begin():
                await session.execute(sql, rows)

    async def on_execute(self, query: str):
        async with self.get_db() as session:
            async with session.begin():
                await session.execute(query)

    async def __aexit__(self, exc_type, exc_value, traceback):
        """退出上下文时不吞噬异常，仅做清理。"""
        return False

    async def cleanup(self):
        if self.engine:
            await self.engine.dispose()
            self.engine = None
            self._session_factory = None
        self._initialized = False


async_ops = AsyncOps()