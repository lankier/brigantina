#!/usr/bin/env python
# -*- mode: python; coding: utf-8; -*-
import sys, os
# для доступа к файлам данных меняем каталог на тот,
# в котором лежит скрипт запуска
dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(dir)

from brigantina import code
# поехали!
code.webapp.run()                       # stand alone server
