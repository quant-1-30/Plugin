# !/usr/bin/env python3
# -*- encoding: utf-8 -*-
"""
Created on 2021-06-15
author by liu
"""
import redis

r = redis.Redis(host='localhost', port=6379, db=0)
# pool = redis.ConnectionPool(host='localhost', port=6379, db=0)
# r = redis.Redis(connection_pool=pool)
# 数据一次性读入redis里面

