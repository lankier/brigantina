#!/usr/bin/env python
# -*- mode: python; coding: utf-8; -*-
import sys, os
import web
# для доступа к файлам данных меняем каталог на тот,
# в котором лежит скрипт запуска
dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(dir)

from brigantina import code
# поехали!
web.wsgi.runwsgi = lambda func, addr=None: web.wsgi.runfcgi(func, addr)
code.webapp.run()
