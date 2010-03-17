#!/usr/bin/env python
# -*- mode: python; coding: utf-8; -*-
# (c) Lankier mailto:lankier@gmail.com
import sys, os, time
import web
from hashlib import md5
from config import admins, drupal_db_args, register_type, session_parameters
import libdb


class DBStore(web.session.DBStore):
    '''оптимизация под postrges'''
    def __getitem__(self, key):
        try:
            return self.db.select(self.table, where="session_id=$key",
                                  vars=locals())[0]
        except IndexError:
            raise KeyError
##         try:
##             s = self.db.select(self.table, where="session_id=$key",
##                                vars=locals())[0]
##             self.db.query('''update sessions set atime=current_timestamp where session_id=$key''', vars=locals())
##         except IndexError:
##             raise KeyError
##         else:
##             return s

    def __setitem__(self, key, value):
        if not value['username']:
            return
        if key in self:
            self.db.query('''update sessions set atime=current_timestamp, username=$username, ip=$ip, message=$message where session_id=$session_id''', vars=value)
        else:
            self.db.insert(self.table, False, **value)

    def cleanup(self, timeout):
        self.db.query("delete from sessions where atime < current_timestamp - interval '%d secs'" % timeout)

## ----------------------------------------------------------------------
## связь с друпалом
## ----------------------------------------------------------------------

if register_type == 'drupal':
    try:
        _drupal_db = web.database(**drupal_db_args)
    except:
        _drupal_db = None

def _drupal_check_password(username, password):
    if _drupal_db is None:
        return True
    try:
        res = _drupal_db.select('users', locals(), where='name=$username')[0]
    except IndexError:
        return False
    digest = md5(password).hexdigest()
    return (digest == res['pass'])

## def get_userid(username):
##     if _drupal_db is None:
##         return ''
##     try:
##         res = _drupal_db.select('users', locals(), where='name=$username')[0]
##     except IndexError:
##         return ''
##     return res.uid

## ----------------------------------------------------------------------
## собственная авторизация
## ----------------------------------------------------------------------

def get_user(username):
    return libdb._db.select('users', locals(), where='username=$username')

def register_user(username, password, email, confirm=None):
    password = md5(password).hexdigest()
    if not confirm:
        libdb._db.insert('users', False, username=username,
                         password=password, email=email)
    else:
        libdb._db.insert('users', False, username=username,
                         password=password, email=email,
                         confirmid=confirm, active=False)

def get_confirm_id():
    rand = os.urandom(16)
    now = time.time()
    id = md5("%s%s%s%s" % (rand, now, web.safestr(web.ctx.ip),
                           session_parameters['secret_key']))
    id = id.hexdigest()
    return id

def confirm_registration(confirmid):
    try:
        res = libdb._db.select('users', locals(),
                               where='confirmid=$confirmid')[0]
    except IndexError:
        return False
    libdb._db.update('users', vars=locals(), active=True,
                     where='confirmid=$confirmid')
    return True

def _internal_check_password(username, password):
    try:
        res = libdb._db.select('users', locals(), where='username=$username')[0]
    except IndexError:
        return False
    if not res.active:
        return False
    digest = md5(password).hexdigest()
    return (digest == res.password)

if register_type == 'drupal':
    check_password = _drupal_check_password
else:
    check_password = _internal_check_password

## ----------------------------------------------------------------------
## функции проверки доступа
## ----------------------------------------------------------------------

def access(what, itemid=None):
    '''what - запрашиваемое действие (edit_book, edit_author, ...)'''
    if what in ('download', ):
        # скачивать разрешено всем
        return True
    if what == 'many_download':
        if not session.username:
            return False
        # не реализовано
        return False
    if not session.username:
        # глобальный запрет для анонимных пользователей
        return False
    if session.username in admins:
        return True
    if what == 'admin':
        # адимнистрировать разрешено только пользователям из списка
        return session.username in admins
    if itemid is None:
        # общий доступ
        return True
    if what.startswith('edit'):
        # проверка на блокировку пользователя
        blocked = libdb.block_user(session.username, action='isblocked')
        if blocked.isblocked:
            # если заблокирован - значит доступа нет
            return False
        if what == 'edit_book':
            # блокировка книги
            book = libdb.get_book_info(itemid)
            if book.permission != 0:
                return False
        return True
    return True

def check_access(what, itemid=None):
    '''проверка доступа
    в случае отказа - вызывается исключение'''
    if not access(what, itemid):
        raise web.forbidden(render.forbidden())
    return True

if __name__ == '__main__':
    print check_password('admin', 'Abc-123')
    print get_userid('admin')
