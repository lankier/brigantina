#!/usr/bin/env python
# -*- mode: python; coding: utf-8; -*-
# (c) Lankier mailto:lankier@gmail.com
import sys, os
import time
import subprocess
import logging
import logging.handlers
from lxml import etree
from xml.sax.saxutils import escape
from markdown import markdown
from unidecode import unidecode

from config import xslt_dir, books_dir, log_file

def get_dsn(db_args):
    dsn = ''
    for k, v in db_args.items():
        if not v: continue
        if k == 'dbn': continue
        if k == 'db': k = 'dbname'
        if dsn: dsn += ' '
        dsn += k+'='+v
    return dsn

def _create_logger():
    fmt = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logger = logging.getLogger('Brigantina')
    logging.basicConfig(format=fmt)
    logger.setLevel(logging.DEBUG)
    handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=1024*1024, backupCount=5)
    logger.addHandler(handler)
    formatter = logging.Formatter(fmt)
    handler.setFormatter(formatter)
    return logger
logger = _create_logger()

def authorname(a):
    '''создаёт полное имя автора:
    firstname middlename lastname (nickname) или
    firstname middlename lastname или
    nickname
    '''
    fn = a.get('firstname', '')
    mn = a.get('middlename', '')
    ln = a.get('lastname', '')
    nn = a.get('nickname', '')
    if nn:
        if not fn and not mn and not ln:
            return nn
        return '%s %s %s (%s)' % (fn, mn, ln, nn)
    return '%s %s %s' % (fn, mn, ln)

def fb2html(xml, stylesheet='main.xsl'):
    xslt = os.path.join(xslt_dir, stylesheet)
    xslt_doc = etree.parse(xslt)
    transform = etree.XSLT(xslt_doc)
    result_tree = transform(xml)
    return etree.tostring(result_tree, encoding='utf-8')

def fb2txt(xml, stylesheet='fb2txt.xsl'):
    xslt = os.path.join(xslt_dir, stylesheet)
    xslt_doc = etree.parse(xslt)
    transform = etree.XSLT(xslt_doc)
    result_tree = transform(xml)
    return str(result_tree)

def annotation2html(ann):
    xml = etree.fromstring(ann)
    return fb2html(xml, 'annotation.xsl')

def text2annotation(txt):
    txt = escape(txt)
    lines = txt.splitlines()
    ann = []
    for s in lines:
        if not s: continue
        ann.append('<p>'+s+'</p>')
    ann = '\n'.join(ann)
    return '<annotation xmlns="http://www.gribuser.ru/xml/fictionbook/2.0">\n'+ann+'\n</annotation>'

def text2html(txt):
    return markdown(txt)

def mime_type(path):
    if not os.path.exists(path):
        raise ValueError("No such file or directory: '%s'" % path)
    cmd = "file --mime --brief --dereference '%s'" % path
    mt = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True
                          ).communicate()[0]
    return mt.strip()

def book_filename(file, book):
    '''генерирует имя файла транслитом'''
    def _conv(s):
        '''заменяет в строке пробелы на _ и преобразует её в транслит'''
        return unidecode(u'_'.join(s.split()))
    fn = []
    fn.append(_conv(book.authors[0].lastname))
    if book.sequences:
        seq = book.sequences[0]
        fn.append(_conv(seq.name))
        fn.append(_conv(str(seq.number)))
    fn.append(_conv(book.title))
    fn.append(_conv(str(book.id)))
    fn = '_'.join(fn)
    for c in '|?*<>":+[]':              # invalid chars in VFAT
        fn = fn.replace(c, '')
    fn = fn[:245]
    return fn

def strsize(size):
    '''преобразует размер в человекочитаемый формат'''
    if size < 1024:
        # байты
        return str(size)+'B'
    if size < 1024*1024:
        s = 'KB'
        size = size / 1024.
    elif size < 1024*1024*1024:
        s = 'MB'
        size = size / 1024. / 1024.
    else:
        s = 'GB'
        size = size / 1024. / 1024. / 1024.
    if size < 10:
        return '%.2f%s' % (size, s)
    elif size < 100:
        return '%.1f%s' % (size, s)
    return '%.0f%s' % (size, s)

def strtime(datetime, format_):
    '''принимает datetime.datetime объект
    возвращает отформатированную стороку'''
    if format_ == 'sec':
        format_ = '%Y-%m-%d %H:%M:%S'
    elif format_ == 'day':
        format_ = '%Y-%m-%d'
    return time.strftime(format_, datetime.timetuple())

def makedir(d):
    '''создаёт подкаталог в каталоге files'''
    dir = str(d)
    if os.path.exists(os.path.join(books_dir, dir)):
        return
    if sys.platform == 'linux2':
        # в ext[23] каталог не может включать более 32000 подкаталогов
        dd = os.path.join(books_dir, '_')
        if not os.path.exists(dd):
            # служебный каталог, в котором будут каталоги 1-1000, 1001-2000 ...
            os.mkdir(dd)
        d = int(d)
        t = d / 1000                    # тысячи
        begin = t * 1000 + 1
        end = t * 1000 + 1000
        dd = os.path.join(books_dir, '_', '%d-%d' % (begin, end))
        if not os.path.exists(dd):
            # каталог files/_/1-1000
            os.mkdir(dd)
        dd = os.path.join(dd, dir)
        if not os.path.exists(dd):
            # каталог files/_/1-1000/1
            os.mkdir(dd)
        # делаем символическую ссылку на реальный каталог
        src = os.path.join('_', '%d-%d' % (begin, end), dir)
        link = os.path.join(books_dir, dir)
        os.symlink(src, link)
    else:
        # TODO
        os.mkdir(os.path.join(books_dir, dir))

if __name__ == '__main__':
    #ann = open('ann.fb2').read()
    #print annotation2html(ann)
    #xml = etree.parse('kript.fb2')
    #print fb2html(xml)
    #print fb2txt(xml)
    #print mime_type(sys.argv[1])
    #import libdb; print book_filename(libdb.get_book(53))
    makedir(12345)

