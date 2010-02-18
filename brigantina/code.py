#!/usr/bin/env python
# -*- mode: python; coding: utf-8; -*-
# (c) Lankier mailto:lankier@gmail.com
import sys, os
import web

from config import session_parameters, log_file, templates_dir
import libdb
from session import DBStore, access
from utils import authorname, strtime, strsize
from plugins import fb2_formats

from edit import *
from pages import *

urls = pages_urls + edit_urls

web.config.session_parameters.update(session_parameters)
web.config.debug = False

webapp = web.application(urls, globals())

def init_session():
    store = DBStore(libdb._db, 'sessions') # используем собственный store
    #store = web.session.DBStore(libdb._db, 'sessions')
    init = dict(username='', message='')
    session = web.session.Session(webapp, store, initializer=init)
    web.config._session = session
    return session
session = init_session()

def is_watched(item, itemid):
    try:
        return libdb.is_watched(session.username, item, itemid)
    except:
        pass
    return False

def get_message():
    msg = session.message
    session.message = ''
    return msg

_globals = {'context': session,
            'access': access,
            'authorname': authorname,
            'is_watched': is_watched,
            'get_message': get_message,
            'strtime': strtime,
            'strsize': strsize,
            'fb2_formats': fb2_formats,
            }
chunkrender = web.template.render(templates_dir, globals=_globals)
# добавляем сомого себя в globals (нужно ли использовать weakref.ref?)
_globals['chunkrender'] = chunkrender

render = web.template.render(templates_dir, base='site', globals=_globals)

## глобальные переменные session, render, chunkrender
## будут видны во всех модулях без импорта
import __builtin__
__builtin__.session = session
__builtin__.chunkrender = chunkrender
__builtin__.render = render

def notfound():
    '''страница 404'''
    return web.notfound(render.not_found())
webapp.notfound = notfound

def internalerror():
    '''внутренняя ошибка'''
    return web.internalerror(render.internal_error())
webapp.internalerror = internalerror

if __name__ == "__main__":
    #logfd = open(log_file, 'a')
    #sys.stdout = logfd
    #sys.stderr = logfd
    start()

