#!/usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
from distutils.core import setup

setup(
    name = 'brigantina',
    version = '0.4.2',
    url = 'http://www.flibusta.net/',
    author = 'lankier',
    author_email = 'lankier@gmail.com',
    description = 'Brigantina',
    license = 'GPLv3',
    scripts = ['start.py'],
    packages = ['brigantina', 'unidecode'],
    )
