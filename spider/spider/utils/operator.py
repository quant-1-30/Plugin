# !/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import asyncio
from twisted.internet import defer
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from contextlib import asynccontextmanager


__all__ = ["async_ops"]



class AsyncOps(object):
    """Local provider class
    It is a set of interface that allow users to access data.
    Because PITD is not exposed publicly to users, so it is not included in the interface.

    To keep compatible with old qlib provider.
    """
    params = ()

    def __init__(self):
        self._initialized = False
        self.engine = None
        self._loop = asyncio.get_event_loop()

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
        """
            a. create all tables
            b. reflect tables
            c. bug --- every restart service result scan model to recreate (rollback)
        """
        # postgresql+psycopg2cffi://user:password@host:port/dbname[?key=value&key=value...]
        # postgresql+psycopg2://me@localhost/mydb
        # postgresql+asyncpg://me@localhost/mydb
        url = f'postgresql+{os.getenv("PGENGINE")}://{os.getenv("PGUSER")}:{os.getenv("PGPWD")}@{os.getenv("PGHOST")}:{os.getenv("PGPORT")}/{os.getenv("PGDB")}'
        engine = create_async_engine(url, 
                               pool_size=int(os.getenv("PGPOOLSIZE")),
                               pool_timeout=int(os.getenv("PGTIMEOUT")),
                               max_overflow=int(os.getenv("PGMAXOVERFLOW")),
                               pool_recycle=int(os.getenv("PGPOOLRECYCLE")), 
                               pool_pre_ping=bool(int(os.getenv("PGPREPING"))),
                               # isolation_level="AUTOCOMMIT"
                               # stream_results = True/ False
                               # autocommit = True/ False
                               # compiled_cache = True/ False
                               echo=bool(int(os.getenv("PGECHO")))).execution_options(compiled_cache={})
        
        self.engine = engine

    @asynccontextmanager
    async def get_db(self):
        # 会话不应该作为实例变量保存
        await self._ensure_initialized()                
        AsyncSessionLocal = sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        session = AsyncSessionLocal()

        try:
            yield session
            # await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
    
    @staticmethod
    def filter_valid_keys(base_obj, insert):
        valid_keys = [column.name for column in base_obj.__table__.columns]
        # 只设置模型中定义的字段
        return {key: value for key, value in insert.items() if key in valid_keys}
    
    async def reset_sequence(self, table_name):
        """重置表的自增序列"""
        async with self.get_db() as session:
            # 获取当前序列名
            result = await session.execute(text(f"""
                SELECT pg_get_serial_sequence('{table_name}', 'id')
            """))
            sequence_name = result.scalar()
            
            if sequence_name:
                # 重置序列
                await session.execute(text(f"""
                    ALTER SEQUENCE {sequence_name} RESTART WITH 1
                """))
                await session.commit()
    
    # @defer.inlineCallbacks
    # def on_query(self, query: str):
    #     """使用 Scrapy 的 defer 机制"""
    #     try:
    #         from twisted.internet.threads import deferToThread
    #         # 在线程中执行异步代码
    #         results = yield deferToThread(self._run_async_query, query)
    #         defer.returnValue(results)
    #     except Exception as e:
    #         print(f"查询错误: {e}")
    #         defer.returnValue([])

    # def _run_async_query(self, query: str):
    #     async def async_wrapper():
    #         async with self.get_db() as session:
    #             if isinstance(query, str):
    #                 query_obj = text(query)
    #             # result = await session.execute(query_obj)
    #             # return result.scalars().all()
    #             # in asynchronous mode, the synchronous yield_per isn't directly applicable.  you can use the stream() method, which allows streaming query results asynchronously.
    #             stream = await session.stream(query_obj)
    #             # stream.scalars() return one field
    #             results = []
    #             async for row in stream:
    #                 # print("result ", row)
    #                 results.append(row)
    #             return results
        
    #     loop = asyncio.new_event_loop()
    #     asyncio.set_event_loop(loop)
    #     try:
    #         return loop.run_until_complete(async_wrapper())
    #     finally:
    #         loop.close()

    @defer.inlineCallbacks
    def on_query(self, query: str):
        try:
            # 将异步函数提交到全局事件循环
            future = asyncio.run_coroutine_threadsafe(self._async_query(query), self._loop)
            results = yield defer.Deferred.fromFuture(future)
            defer.returnValue(results)
        except Exception as e:
            print(f"查询错误: {e}")
            defer.returnValue([])

    async def _async_query(self, query: str):
        async with self.get_db() as session:
            if isinstance(query, str):
                query_obj = text(query)
            stream = await session.stream(query_obj)
            results = []
            async for row in stream:
                results.append(row)
            return results

    async def on_insert(self, sql:str, param:dict):
        # await self._ensure_initialized()
        async with self.get_db() as session:
            async with session.begin():
                await session.execute(sql, param)
                await session.commit()

    async def on_execute(self, query: str):
        async with self.get_db() as session:
            async with session.begin():
                await session.execute(query)
                await session.commit()

    async def __aexit__(self, exc_type, exc_value, traceback):
            if exc_type is not None:
                print(f"Error: {exc_type}, {exc_value}, {traceback}")
            # True mean suppress exception
            return True
    
    async def cleanup(self):
        if self.engine:
            await self.engine.dispose()
            self.engine = None
        self._initialized = False


async_ops = AsyncOps()

