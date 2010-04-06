#!/usr/bin/env python
# -*- mode: python; coding: utf-8; -*-
# (c) Lankier mailto:lankier@gmail.com
import sys, os
import zipfile
import traceback
import subprocess
from lxml import etree
import web

import libdb
from utils import book_filename
from config import books_dir, xslt_dir, fb2_rtf_dir
from updatefb2 import update_fb2

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

def save_zip_many(files, out_file):
    zf = zipfile.ZipFile(out_file, 'w', zipfile.ZIP_STORED)
    for f in files:
        fn = os.path.basename(f)
        zf.write(f, fn, zipfile.ZIP_DEFLATED)

## ----------------------------------------------------------------------
## функции для работы с fb2
## ----------------------------------------------------------------------

fb2_formats = ['fb2', 'txt', 'html', 'rtf'] # в какие форматы можно преобразовать

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

def fb2_to_txt(txt_path, fb2_path=None, xml=None, stylesheet='totxt.xsl'):
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

def fb2_fb2_zip(fileid, fb2_path, fn):
    fn += '.fb2'
    dir = os.path.join(books_dir, fileid)
    path = os.path.join(dir, fn+'.zip')
    if not os.path.exists(path):
        save_zip(path, fn, fb2_path)
    return path

def fb2_html_zip(fileid, fb2_path, fn, xml=None):
    fn += '.html'
    dir = os.path.join(books_dir, fileid)
    zip_path = os.path.join(dir, fn+'.zip') # полный путь к zip
    if os.path.exists(zip_path):
        return zip_path
    html_path = os.path.join(dir, fileid+'.html')
    if not os.path.exists(html_path):
        # если html отсутствует - создаём
        fb2_to_html(html_path, fb2_path, xml)
    # создаём zip
    images = libdb.file_get_images(fileid)
    images = [os.path.join(dir, i) for i in images]
    save_zip(zip_path, fn, html_path, images)
    return zip_path

def fb2_txt_zip(fileid, fb2_path, fn, xml=None, stylesheet='totxt.xsl'):
    fn += '.txt'
    dir = os.path.join(books_dir, fileid)
    zip_path = os.path.join(dir, fn+'.zip') # путь к файлу с архивом
    if os.path.exists(zip_path):
        return zip_path
    txt_path = os.path.join(dir, fileid+'.txt')
    if not os.path.exists(txt_path):
        # если txt отсутствует - создаём
        fb2_to_txt(txt_path, fb2_path, xml)
    # создаём zip
    images = libdb.file_get_images(fileid)
    images = [os.path.join(dir, i) for i in images]
    save_zip(zip_path, fn, txt_path, images)
    return txt_path

def fb2_rtf_zip(fileid, fb2_path, fn):
    fn += '.rtf'
    dir = os.path.join(books_dir, fileid)
    zip_path = os.path.join(dir, fn+'.zip')
    if os.path.exists(zip_path):
        return zip_path
    rtf_path = os.path.join(dir, fileid+'.rtf')
    if not os.path.exists(rtf_path):
        tortf_cmd = ("perl %s/fb2_2_rtf.pl %s %s/FB2_2_rtf.xsl %s -mute" %
                     (fb2_rtf_dir, fb2_path, fb2_rtf_dir, rtf_path))
        p = subprocess.Popen(tortf_cmd, shell=True)
        os.waitpid(p.pid, 0)
    save_zip(zip_path, fn, rtf_path)
    return zip_path

def fb2_get(fileid, filetype):
    '''возвращает путь к архиву с файлом заданного формата
    (fb2, html, ...)
    создаёт архив при его отсутствии'''
    if filetype not in fb2_formats:
        return None
    dir = os.path.join(books_dir, fileid)
    file = libdb.get_file(fileid)
    book = None
    if not file:
        return None
    if file.filetype != 'fb2':
        return None
    libdb.update_download_stat(session.username, fileid, filetype)
    fn = file.filename              # имя файла транслитом без расширения
    if not fn:
        # нет сохранённого имени файла - генерируем
        book = libdb.get_book(file.books[0].id)
        fn = book_filename(file, book)
        # сохраняем
        libdb.file_update_filename(fileid, fn)
    fb2_path = os.path.join(dir, fileid+'.fb2') # путь к оригинальному fb2
    new_path = os.path.join(dir, fileid+'-up.fb2') # путь к обновлённому fb2
    zp = os.path.join(dir, fn+'.'+filetype+'.zip') # путь к файлу для скачивания
    if file.needupdate:
        if not book:
            book = libdb.get_book(file.books[0].id)
        # удаляем старые файлы
        if os.path.exists(new_path):
            os.remove(new_path)
        if os.path.exists(zp):
            os.remove(zp)
        # обновляем
        fb2 = update_fb2(fb2_path, book, fileid)
        # записываем
        open(new_path, 'w').write(fb2)
        libdb.reset_need_update(fileid)
        # новое имя файла
        fn = book_filename(file, book)
        zp = os.path.join(dir, fn+'.'+filetype+'.zip')
        libdb.file_update_filename(fileid, fn)
    if os.path.exists(new_path):
        # есть обновлённый файл - используем его
        fb2_path = new_path
    if not os.path.exists(zp):
        # файл (zip) отсутствует - создаём
        func = globals()['fb2_'+filetype+'_zip']
        zp = func(fileid, fb2_path, fn)
    return zp

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
        book = libdb.get_book_info(file.books[0].id)
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
    session = web.Storage(username='')
    print fb2_get('4', 'fb2')
    pass
    
