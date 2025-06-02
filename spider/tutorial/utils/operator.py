# !/usr/bin/env python3
# -*- coding: utf-8 -*-

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from contextlib import asynccontextmanager

from tutorial.meta import with_metaclass, MetaSingleton

__all__ = ["async_ops"]


class AsyncOps(with_metaclass(MetaSingleton, object)):
    """Local provider class
    It is a set of interface that allow users to access data.
    Because PITD is not exposed publicly to users, so it is not included in the interface.

    To keep compatible with old qlib provider.
    select and insert in seprate mode / begin used in insert / select just session is ok
    """
    # SQLALCHEMY_DATABASE_URL = f"sqlite:///{SQLITE_DB_PATH}" # dsn
    params = (
        ("host", "localhost"),
        ("port", "5432"),
        ("user", "postgres"),
        ("pwd", "20210718"),
        ("db", "bt_oms"),
        ("engine", "psycopg"),
        ("pool_size", 20),
        ("max_overflow", 10),
        ("pool_recycle", 3600),
        ("pool_pre_ping", True),
        ("echo", True)
    )

    def __init__(self):
        self._initialized = False

    async def __aenter__(self):
        await self.initialize()
        return self
    
    async def initialize(self):
        """Async initialization method"""
        if self._initialized:
            return
        await self._build_engine()
        self._initialized = True

    async def _build_engine(self):
        """
            a. create all tables
            b. reflect tables
            c. bug --- every restart service result scan model to recreate (rollback)
        """
        # postgresql+psycopg2cffi://user:password@host:port/dbname[?key=value&key=value...]
        # postgresql+psycopg2://me@localhost/mydb
        # postgresql+asyncpg://me@localhost/mydb
        print("builder ", self)
        url = f"postgresql+{self.p.engine}://{self.p.user}:{self.p.pwd}@{self.p.host}:{self.p.port}/{self.p.db}"
        # READ COMMITTED
        # READ UNCOMMITTED
        # REPEATABLE READ
        # SERIALIZABLE
        engine = create_async_engine(url, 
                               pool_size=self.p.pool_size, 
                               max_overflow=self.p.max_overflow,
                               # 每小时回收连接
                               pool_recycle=3600, 
                               # 使用 ping 检查连接有效性 
                               pool_pre_ping=self.p.pool_pre_ping,
                               # stream_results = True/ False
                               # autocommit = True/ False
                               # compiled_cache = True/ False
                               # isolation_level = "AUTOCOMMIT"
                               echo=self.p.echo).execution_options(compiled_cache={})
        setattr(self, "engine", engine)

    @asynccontextmanager
    async def get_db(self):
        AsyncSessionLocal = sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        session = AsyncSessionLocal()
        print("session", session)
        try:
                yield session
        finally:
                await session.close()
    
    async def on_query(self, query, params):
        async with self.get_db() as session:
            # stmt = select(cal).execution_options(**self.options)
            # AsyncSession not support query 
            # result = await session.execute(query)
            # yield result.scalars().all()
            # in asynchronous mode, the synchronous yield_per isn't directly applicable. 
            # Instead, you can use the stream() method, which allows streaming query results asynchronously.
            row = await session.execute(query, params)
            # stream.scalars() return one field
            # async for row in stream.scalars():
            return row.scalars().all()

    async def on_insert(self, sql, params):
        async with self.get_db() as session:
            async with session.begin():
                result = await session.execute(sql, params)
                insert_result = result.fetchone()
                return insert_result

    async def __aexit__(self, exc_type, exc_value, traceback):
            if exc_type is not None:
                print(f"Error: {exc_type}, {exc_value}, {traceback}")
            # True mean suppress exception
            return True
    
    async def cleanup(self):
        # 释放所有连接，断开数据库 / 清理的
        self.engine.dispose()
        print("cleanup")


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
