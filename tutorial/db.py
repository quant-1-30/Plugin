# !/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Mar 12 15:37:47 2019

@author: python
"""
from sqlalchemy import create_engine
from .settings import MYSQL


def init_engine():
    # 在这里导入定义模型所需要的所有模块，这样它们就会正确的注册在
    # 元数据上。否则你就必须在调用 init_db() 之前导入它们, import --- 执行脚本
    # scoped_session 线程安全
    # from sqlalchemy.orm import sessionmaker, scoped_session
    # db_session = scoped_session(sessionmaker(autocommit=False,
    #                                          autoflush=False,
    #                                          bind=engine))
    # from sqlalchemy.ext.declarative import declarative_base
    # Base = declarative_base()
    # Base.query = db_session.query_property()
    # Base.metadata.create_all(bind=engine)
    engine_path = 'mysql+pymysql://{username}:{password}@{host}:{port}'.format(**MYSQL)
    eng = create_engine(engine_path, pool_size=MYSQL['pool_size'],
                        max_overflow=MYSQL['max_overflow'])
    create_str = "CREATE DATABASE IF NOT EXISTS %s ;" % MYSQL['db']
    eng.execute(create_str)
    # engine.execute("use %s" % params['db'])
    engine_path = 'mysql+pymysql://{username}:{password}@{host}:{port}/{db}'.format(**MYSQL)
    eng = create_engine(engine_path, pool_size=MYSQL['pool_size'],
                        max_overflow=MYSQL['max_overflow'])
    return eng


def get_db_con():
    con = engine.connect()
    return con


# metadata 初始化之后metadata.tables固定了
engine = init_engine()
