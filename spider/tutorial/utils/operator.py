# !/usr/bin/env python3
# -*- coding: utf-8 -*-

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from contextlib import asynccontextmanager
from sqlalchemy.sql import text


__all__ = ["async_ops"]


class AsyncOps(object):
    """Local provider class
    It is a set of interface that allow users to access data.
    Because PITD is not exposed publicly to users, so it is not included in the interface.

    To keep compatible with old qlib provider.
    select and insert in seprate mode / begin used in insert / select just session is ok
    """
    def __init__(self):
        self._initialized = False
        self.engine = None
        self.session = None

    async def __aenter__(self, crawler=None):
        await self.initialize(crawler)
        return self
    
    async def initialize(self, crawler):
        """Async initialization method"""
        if self._initialized:
            return
        await self._build_engine(crawler)
        self._initialized = True

    async def _build_engine(self, crawler=None):
        """
            a. create all tables
            b. reflect tables
            c. bug --- every restart service result scan model to recreate (rollback)
        """
        if crawler:
            url = f"postgresql+{crawler.settings.get('POSTGRES_ENGINE')}://{crawler.settings.get('POSTGRES_USER')}:{crawler.settings.get('POSTGRES_PASSWORD')}@{crawler.settings.get('POSTGRES_HOST')}:{crawler.settings.get('POSTGRES_PORT')}/{crawler.settings.get('POSTGRES_DB')}"
            self.engine = create_async_engine(
                url,
                pool_size=crawler.settings.getint('POSTGRES_POOL_SIZE'),
                max_overflow=crawler.settings.getint('POSTGRES_MAX_OVERFLOW'),
                pool_recycle=crawler.settings.getint('POSTGRES_POOL_RECYCLE'),
                pool_pre_ping=crawler.settings.getbool('POSTGRES_POOL_PRE_PING'),
                echo=crawler.settings.getbool('POSTGRES_ECHO')
            )
        else:
            # 使用默认配置
            url = "postgresql+asyncpg://postgres:20210718@localhost:5432/bt_feed"
            self.engine = create_async_engine(
                url,
                pool_size=20,
                max_overflow=10,
                pool_recycle=3600,
                pool_pre_ping=True,
                echo=True
            )

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

    @asynccontextmanager
    async def get_db(self):
        if not self.session:
            async_session = sessionmaker(
                self.engine, class_=AsyncSession, expire_on_commit=False
            )
            self.session = async_session()
        try:
            yield self.session
        finally:
            await self.session.close()
            self.session = None
    
    async def on_query(self, query, params):
        async with self.get_db() as session:
            result = await session.execute(query, params)
            return result.scalars().all()

    async def on_insert(self, sql, params):
        async with self.get_db() as session:
            async with session.begin():
                await session.execute(sql, params)
                await session.commit()

    async def __aexit__(self, exc_type, exc_value, traceback):
        if exc_type is not None:
            print(f"Error: {exc_type}, {exc_value}, {traceback}")
        return True
    
    async def cleanup(self):
        if self.engine:
            await self.engine.dispose()
            self.engine = None
        self._initialized = False

async_ops = AsyncOps()

# def init_engine():
#     # 在这里导入定义模型所需要的所有模块，这样它们就会正确的注册在
#     # 元数据上。否则你就必须在调用 init_db() 之前导入它们, import --- 执行脚本
#     # scoped_session 线程安全
#     # from sqlalchemy.orm import sessionmaker, scoped_session
#     # db_session = scoped_session(sessionmaker(autocommit=False,
#     #                                          autoflush=False,
#     #                                          bind=engine))
#     # from sqlalchemy.ext.declarative import declarative_base
#     # Base = declarative_base()
#     # Base.query = db_session.query_property()
#     # Base.metadata.create_all(bind=engine)
#     engine_path = 'mysql+pymysql://{username}:{password}@{host}:{port}'.format(**MYSQL)
#     eng = create_engine(engine_path, pool_size=MYSQL['pool_size'],
#                         max_overflow=MYSQL['max_overflow'])
#     create_str = "CREATE DATABASE IF NOT EXISTS %s ;" % MYSQL['db']
#     eng.execute(create_str)
#     eng.execute("use %s" % MYSQL['db'])
#     # engine_path = 'mysql+pymysql://{username}:{password}@{host}:{port}/{db}'.format(**MYSQL)
#     # eng = create_engine(engine_path, pool_size=MYSQL['pool_size'],
#     #                     max_overflow=MYSQL['max_overflow'])
#     return eng
