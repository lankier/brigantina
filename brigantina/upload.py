#!/usr/bin/env python
# -*- mode: python; coding: utf-8; -*-
# (c) Lankier mailto:lankier@gmail.com
#
# $Id$
#
import sys, os
import time
import shutil
import subprocess
import zipfile
import web
import traceback

from config import upload_dir
from utils import mime_type, logger
import addfile
import libdb

class UploadError(Exception):
    pass

def _upload(unzip=True):
    '''загрузка файлов
    если это zip - распаковываем
    возвращает список загруженных файлов'''
    x = web.input(file={})
    # создём каталог с именем пользователя
    username = session.username
    if not username:
        username = 'anonimous'
    if isinstance(username, unicode):
        try:
            username = username.encode('utf-8')
        except:
            username = 'anonimous'
    out_dir = os.path.join(upload_dir, username)
    if os.path.exists(out_dir) and not os.path.isdir(out_dir):
        raise UploadError(u'Файл существует, но это не каталог')
    if not os.path.exists(out_dir):
        os.mkdir(out_dir)
    # записываем полученные данные в файл
    fn = time.strftime('%Y-%m-%d-%H-%M-%S')
    outfile = os.path.join(out_dir, fn)
    outfd = open(outfile, 'wb')
    data = True
    while data:
        data = x['file'].file.read(1024)
        outfd.write(data)
    outfd.close()
    # проверка - это архив?
    if unzip:
        tmp_dir = os.path.join(out_dir, 'tmp')
        if not os.path.exists(tmp_dir):
            os.mkdir(tmp_dir)
        if zipfile.is_zipfile(outfile):
            p = subprocess.Popen("unzip -o -j -d '%s' '%s'" % (tmp_dir, outfile),
                                 shell=True)
            os.waitpid(p.pid, 0)
            files = [os.path.join(tmp_dir, f) for f in os.listdir(tmp_dir)]
        elif mime_type(outfile).startswith('application/x-rar'):
            p = subprocess.Popen("unrar e -y -p- '%s' '%s'" % (outfile, tmp_dir),
                                 shell=True)
            os.waitpid(p.pid, 0)
            files = [os.path.join(tmp_dir, f) for f in os.listdir(tmp_dir)]
        else:
            files = [outfile]
    else:
        files = [outfile]
    return files

def upload_fb2():
    files = _upload()
    # проходим по всем полученным файлам
    added = []
    for f in files:
        storage = web.Storage(
            filename=f,
            filetype='fb2',
            bookid=None,                # id книги куда добавили файл
            fileid=None,                # id файла
            newbook=True,               # создали новую книгу?
            validation_errors=[], # сюда добавляем ошибки при валидации (несмертельные)
            error=None,           # смертельные ошибки
            )
        added.append(storage)
        try:
            # используем транзакцию
            ta = libdb._db.transaction()
            try:
                bookid, fileid, newbook = addfile.add_fb2_file(f, storage.validation_errors)
            except:
                ta.rollback()
                raise
            else:
                ta.commit()
        except addfile.FB2ParseError, err:
            storage.error = err
        else:
            storage.bookid = bookid
            storage.fileid = fileid
            storage.newbook = newbook
        if os.path.exists(f):
            os.remove(f)
    return added

def upload_other(bookid):
    f = _upload(False)[0]
    i = web.input(file={})
    origname = i['file'].filename           # оригинальное имя файла
    filetype = i['filetype'][:5]
    storage = web.Storage(
        filename=f,
        origname=origname,
        filetype=filetype,
        bookid=bookid,
        fileid=None,
        newbook=False,
        validation_errors=[],
        error=None,
        )
    ta = libdb._db.transaction()
    try:
        fileid = addfile.add_other_file(storage, bookid)
    except Exception, err:
        ta.rollback()
        traceback.print_exc()
        storage.error = err
    else:
        ta.commit()
        storage.fileid = fileid
    if os.path.exists(f):
        os.remove(f)
    return [storage]

