#!/usr/bin/env python
# -*- mode: python; coding: utf-8; -*-
import sys, os
# для доступа к файлам данных меняем каталог на тот,
# в котором лежит скрипт запуска
dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(dir)
sys.path.append(dir)                    # wsgi

from brigantina import code, config

# logging
#sys.stderr = open(config.log_file, 'a')

# поехали!
#code.start()                            # stand alone server
application = code.webapp.wsgifunc()    # wsgi
