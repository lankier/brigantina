#!/usr/bin/env python
# -*- mode: python; coding: utf-8; -*-
# (c) Lankier mailto:lankier@gmail.com
import sys, os
import zipfile
import traceback
from lxml import etree
import web

import libdb
from utils import book_filename
from config import books_dir, xslt_dir

def save_zip(out_file, out_fn, in_file, images=None, from_str=False):
    '''записываем в out_file файл in_file под именем out_fn
    при необходимости добавляем images'''
    zf = zipfile.ZipFile(out_file, 'w', zipfile.ZIP_DEFLATED)
    if from_str:
        zipinfo = zipfile.ZipInfo()
        zipinfo.filename = out_fn
        zipinfo.external_attr = 0644 << 16L
        zipinfo.compress_type = zipfile.ZIP_DEFLATED
        zf.writestr(zipinfo, in_file)
    else:
        zf.write(in_file, out_fn, zipfile.ZIP_DEFLATED)
    if images:
        # добавляем изображения
        for i in images:
            fn = os.path.basename(i)
            zf.write(i, fn, zipfile.ZIP_DEFLATED)

## ----------------------------------------------------------------------
## функции для работы с fb2
## ----------------------------------------------------------------------

fb2_formats = ['fb2', 'txt', 'html']    # в какие форматы можно преобразовать

def _xslt(xml, stylesheet):
    xslt = os.path.join(xslt_dir, stylesheet)
    xslt_doc = etree.parse(xslt)
    transform = etree.XSLT(xslt_doc)
    result_tree = transform(xml)
    return result_tree

def fb2_to_html(html_path, fb2_path=None, xml=None,
                stylesheet='tohtml.xsl'): # main.xsl ?
    '''генерирует html и сохраняет в html_path'''
    if not xml:
        assert fb2_path
        xml = etree.parse(fb2_path)
    result_tree = _xslt(xml, stylesheet)
    html = etree.tostring(result_tree, encoding='utf-8')
    open(html_path, 'w').write(html)
    return html_path

def fb2_to_txt(txt_path, fb2_path=None, xml=None,
               stylesheet='totxt.xsl'):
    '''генерирует txt и сохраняет в txt_path
    если txt_path is None - возвращает txt'''
    if not xml:
        assert fb2_path
        xml = etree.parse(fb2_path)
    result_tree = _xslt(xml, stylesheet)
    txt = str(result_tree)
    if txt_path is None:
        return txt
    open(txt_path, 'w').write(txt)
    return txt_path

def fb2_read(fileid, xml=None):
    '''возвращает путь к html файлу
    при отсутствии генерирует его'''
    file = libdb.get_file_info(fileid)
    if not file:
        return None
    if file.filetype != 'fb2':
        return None
    libdb.update_download_stat(session.username, fileid, 'read')
    dir = os.path.join(books_dir, fileid)
    html_path = os.path.join(dir, fileid+'.html')
    if not os.path.exists(html_path):
        fb2_path = os.path.join(dir, fileid+'.fb2')
        fb2_to_html(html_path, fb2_path, xml)
    return html_path

def fb2_fb2_zip(fileid, fn):
    fn += '.fb2'
    dir = os.path.join(books_dir, fileid)
    path = os.path.join(dir, fn+'.zip')
    if not os.path.exists(path):
        fb2_path = os.path.join(dir, fileid+'.fb2')
        save_zip(path, fn, fb2_path)
    return path

def fb2_html_zip(fileid, fn, xml=None):
    fn += '.html'
    dir = os.path.join(books_dir, fileid)
    zip_path = os.path.join(dir, fn+'.zip') # полный путь к zip
    if os.path.exists(zip_path):
        return zip_path
    html_path = os.path.join(dir, fileid+'.html')
    if not os.path.exists(html_path):
        # если html отсутствует - создаём
        fb2_path = os.path.join(dir, fileid+'.fb2')
        fb2_to_html(html_path, fb2_path, xml)
    # создаём zip
    images = libdb.file_get_images(fileid)
    images = [os.path.join(dir, i) for i in images]
    save_zip(zip_path, fn, html_path, images)
    return zip_path

def fb2_txt_zip(fileid, fn, xml=None, stylesheet='totxt.xsl'):
    fn += '.txt'
    dir = os.path.join(books_dir, fileid)
    zip_path = os.path.join(dir, fn+'.zip') # путь к файлу с архивом
    if os.path.exists(zip_path):
        return zip_path
    txt_path = os.path.join(dir, fileid+'.txt')
    if not os.path.exists(txt_path):
        # если txt отсутствует - создаём
        fb2_path = os.path.join(dir, fileid+'.fb2')
        fb2_to_txt(txt_path, fb2_path, xml)
    # создаём zip
    images = libdb.file_get_images(fileid)
    images = [os.path.join(dir, i) for i in images]
    save_zip(zip_path, fn, txt_path, images)
    return txt_path

def fb2_get(fileid, filetype):
    '''возвращает путь к архиву с файлом заданного формата
    (fb2, html, ...)
    создаёт архив при его отсутствии'''
    if filetype not in fb2_formats:
        return None
    dir = os.path.join(books_dir, fileid)
    file = libdb.get_file_info(fileid)
    if not file:
        return None
    if file.filetype != 'fb2':
        return None
    libdb.update_download_stat(session.username, fileid, filetype)
    fn = file.filename              # имя файла транслитом без расширения
    if not fn:
        # нет сохранённого имени файла - генерируем
        libdb.add_books_to_file(file)
        book = libdb.get_book(file.books[0].id)
        fn = book_filename(file, book)
        # сохраняем
        libdb.file_update_filename(fileid, fn)
    path = os.path.join(dir, fn+'.'+filetype+'.zip')
    if not os.path.exists(path):
        # файл (zip) отсутствует - создаём
        func = globals()['fb2_'+filetype+'_zip']
        path = func(fileid, fn)
    return path

## ----------------------------------------------------------------------
## функции для работы с не fb2
## ----------------------------------------------------------------------

def other_zip(fileid, fn, ext):
    fn += ext
    dir = os.path.join(books_dir, fileid)
    path = os.path.join(dir, fn+'.zip')
    if not os.path.exists(path):
        orig_path = os.path.join(dir, fileid+ext)
        save_zip(path, fn, orig_path)
    return path

def other_get(fileid):
    dir = os.path.join(books_dir, fileid)
    file = libdb.get_file_info(fileid)
    if not file:
        return None
    if file.filetype == 'fb2':
        return fb2_get(fileid, 'fb2')
    libdb.update_download_stat(session.username, fileid, 'orig')
    fn = file.filename              # имя файла транслитом без расширения
    if not fn:
        # нет сохранённого имени файла - генерируем
        libdb.add_books_to_file(file)
        book = libdb.get_book(file.books[0].id)
        fn = book_filename(file, book)
        # сохраняем
        libdb.file_update_filename(fileid, fn)
    ext = file.origext
    # упаковывать или не упаковывать? вот в чём вопрос...
    if 1: #ext in ('.zip', '.rar', '.7z', '.gz', '.bz2', '.djvu', '.pdf'):
        # не упаковываем
        path = os.path.join(dir, fn+ext)
        if not os.path.exists(path):
            # FIXME: UNIX only
            os.symlink(fileid+ext, path)
        return path
    # упаковываем
    path = os.path.join(dir, fn+ext+'.zip')
    if not os.path.exists(path):
        # файл (zip) отсутствует - создаём
        path = other_zip(fileid, fn, ext)
    return path


if __name__ == '__main__':
    pass
    
