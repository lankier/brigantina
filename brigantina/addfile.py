#!/usr/bin/env python
# -*- mode: python; coding: utf-8; -*-
# (c) Lankier mailto:lankier@gmail.com
import sys, os, time
import shutil
import traceback
from lxml import etree
from hashlib import md5
from base64 import b64decode
import web

import validator
import libdb
import plugins
from config import books_dir, generate_when_adding
from utils import annotation2html, authorname, makedir, logger

namespaces = {'m': 'http://www.gribuser.ru/xml/fictionbook/2.0',
              'xlink':'http://www.w3.org/1999/xlink',
              'l':'http://www.w3.org/1999/xlink'}

class FB2ParseError(Exception):
    pass

def get_md5(fn):
    m = md5()
    fd = open(fn)
    while True:
        s = fd.read(1024)
        if not s:
            break
        m.update(s)
    md5digest = m.hexdigest()
    if not libdb.check_file(md5digest):
        raise FB2ParseError(u'Такой файл уже есть')
    return md5digest

_xpath_cash = {}
def xpath(path):
    # optimisation
    if path in _xpath_cash:
        return _xpath_cash[path]
    find = etree.XPath(path, namespaces=namespaces)
    _xpath_cash[path] = find
    return find

def get_elem(xml, prefix, elem):
    find = xpath(prefix+'/m:'+elem)
    e = find(xml)
    if not e or not e[0].text:
        return None
    return e[0].text.strip()

def get_authors(xml, prefix='author',
                main_prefix='/m:FictionBook/m:description/m:title-info'):
    '''возвращает список авторов (prefix=author)
    или переводчиков (prefix=translator)
    или авторов файла'''
    tags = ('first-name', 'middle-name', 'last-name',
             'nickname', 'home-page', 'email')
    prefix = main_prefix+'/m:'+prefix
    allauthors = []
    find = xpath(prefix)
    authors = find(xml)
    for a in authors:
        astor = web.Storage()
        #for n in tags:
        #    astor[n.replace('-', '')] = ''
        for name in a:
            # ugly...
            tag = name.tag.replace(
                '{http://www.gribuser.ru/xml/fictionbook/2.0}', '')
            if tag in tags:
                if name.text:
                    text = name.text.strip()
                else:
                    text = ''
                tag = tag.replace('-', '')
                astor[tag] = text
        allauthors.append(astor)
    return allauthors

def get_sequences(xml, xpath_prefix):
    find = xpath(xpath_prefix+'/m:sequence')
    sequences = find(xml)
    allsequences = []
    for seq in sequences:
        sequencename = seq.attrib.get('name')
        if not sequencename:
            # плохой файл
            continue
        sequencename = sequencename.strip()
        sequencenumber = seq.attrib.get('number', '0').strip() # если номер отсутствует - ставим 0
        try:
            sequencenumber = int(sequencenumber)
        except ValueError:
            sequencenumber = 0
        allsequences.append((sequencename, sequencenumber))
    return allsequences

def get_year(xml, prefix='/m:FictionBook/m:description/m:title-info/m:date'):
    # <date value="2004-04-16">2004</date>
    year = 0
    find = xpath(prefix)
    year_tag = find(xml)
    if year_tag:
        year_tag = year_tag[0]
        # попробуем взять год из атрибута value
        year_value = year_tag.attrib.get('value')
        try:
            year = time.strptime(year_value, '%Y-%m-%d').tm_year
        except:
            # попробуем взять год из тега
            # подходит и "2004-04-16" и "2004"
            try:
                year_text = year_tag.text.split('-')[0]
                year = int(year_text)
            except:
                pass
    return year

def save_binaries(xml, dir, fileid, save_files=True):
    '''извлекает все изображения из fb2-файла
    сохраняет их в каталоге dir
    возвращает список из (имя, content-type) сохраненных обложек'''
    images = set()
    xp = '/m:FictionBook/m:binary'
    find = xpath(xp)
    for binary in find(xml):
        # ищем и сохраняем все изображения
        try:
            data = b64decode(binary.text)
        except:
            continue
        id = binary.attrib.get('id')
        if not id:
            continue
        if save_files:
            if '/' in id or '\\' in id:
                # security
                pass
            else:
                try:
                    open(os.path.join(dir, id), 'wb').write(data)
                except:
                    traceback.print_exc()
        images.add(id)
    images = list(images)
    # ищем ссылки на обложки
    xp = '/m:FictionBook/m:description/m:title-info/m:coverpage/m:image'
    find = xpath(xp)
    allcovers = find(xml)
    covers = []
    for cover in allcovers:
        # здесь coverid == имя файла
        coverid = cover.attrib.get('{http://www.w3.org/1999/xlink}href')
        if not coverid:
            continue
        coverid = coverid[1:] # убираем '#'
        #coverid = coverid.lower()
        if coverid in images:
            covers.append(coverid)
    libdb.add_images(fileid, images, covers)
    return images, covers

def save_annotation(xml, bookid, fileid):
    find = xpath('/m:FictionBook/m:description/m:title-info/m:annotation')
    annotation = find(xml)
    if not annotation:
        return
    ann = annotation[0]
    ann = etree.tostring(ann, encoding='utf-8')
    html = annotation2html(ann)
    libdb.add_book_desc(bookid, fileid, ann, html)

def save_description(xml, fileid):
    '''сохраняем fb2 description'''
    find = xpath('/m:FictionBook/m:description')
    desc = find(xml)[0]
    context = etree.iterwalk(desc, events=("start", "end"))
    queue = []
    desc = []
    for action, elem in context:
        if action == 'start':
            if isinstance(elem.tag, (str, unicode)):
                tag = elem.tag
            else:
                tag = '<!--comment-->'
            tag = tag.replace('{http://www.gribuser.ru/xml/fictionbook/2.0}', '')
            queue.append(tag)
            path = '/'.join(queue)
            if elem.text:
                text = ' '.join(elem.text.split())
            else:
                text = ''
            for n, v in elem.attrib.items():
                n = n.replace('{http://www.w3.org/1999/xlink}', '')
                desc.append(path + ('@%s: %s' % (n, v)))
            desc.append('%s: %s' % (path, text))
        elif action == 'end':
            del queue[-1]
    desc = '\n'.join(desc)
    libdb.save_file_description(fileid, desc)

def add_fb2_file(fn, errors):
    '''парсинг fb2 файла и добавление файла в базу
    возвращаем bookid, fileid и флаг-создание новой книги
    (если создана новая книга флаг = True, иначе False)'''
    session.hide_username = True
    # md5
    md5digest = get_md5(fn)
    # валидация (в процессе которой создаётся xml)
    xml = validator.check_file(fn, errors)
    if xml is None:
        raise FB2ParseError(u'Похоже это не fb2')
    # filesize
    filesize = os.path.getsize(fn)
    if filesize >= 2147483647:
        raise FB2ParseError(u'Слишком большой файл')
    # парсинг fb2
    xpath_prefix = '/m:FictionBook/m:description/m:title-info'
    # <title-info>
    #   <book-title>
    title = get_elem(xml, xpath_prefix, 'book-title')
    if not title:
        raise FB2ParseError(u'Отсутствует название книги')
    #   <lang>
    # язык оригинала - добавляется к книге
    lang = get_elem(xml, xpath_prefix, 'src-lang')
    # язык издания - добавляется к файлу
    publlang = get_elem(xml, xpath_prefix, 'lang')
    #   <date> (year)
    # год написания книги
    year = get_year(xml)
    # год публикации
    publyear = get_elem(xml, '/m:FictionBook/m:description/m:publish-info',
                        'year')
    try:
        publyear = int(publyear)
    except:
        publyear = 0
    #   <author>
    allauthors = get_authors(xml)
    if not allauthors:
        raise FB2ParseError('В файле не указан автор книги')
    #   <translator>
    alltranslators = get_authors(xml, 'translator')
    #   <genre>
    find = xpath(xpath_prefix+'/m:genre')
    genres = find(xml)
    allgenres = []
    for gen in genres:
        allgenres.append(gen.text.strip())
    #   <sequence>
    # авторские сериалы
    allsequences = get_sequences(xml, xpath_prefix)
    # издательские серии
    allpublsequences = get_sequences(xml, '/m:FictionBook/m:description/m:publish-info')
    # fb2 id, version
    fb2id = get_elem(xml, '/m:FictionBook/m:description/m:document-info', 'id')
    v = get_elem(xml, '/m:FictionBook/m:description/m:document-info', 'version')
    try:
        fb2version = float(v)
    except:
        fb2version = None
    # авторы файла
    fa = get_authors(xml, 'author',
                     '/m:FictionBook/m:description/m:document-info')
    fileauthor = ', '.join(authorname(a).strip() for a in fa)
    fileauthor = fileauthor
    # создаем новую книгу или добавляем файл в уже существующую
    bookid, newbook = add_book(title, allauthors, allgenres, allsequences,
                               year=year, lang=lang,
                               publyear=publyear, publlang=publlang)
    # создаём txt
    txt = plugins.fb2_to_txt(None, xml=xml)
    textsize = len(txt)
    # записываем инф-цию о файле в базу
    bookfile = web.Storage(title=title, md5=md5digest, filetype='fb2',
                           filesize=filesize, textsize=textsize,
                           fb2id=fb2id, fb2version=fb2version,
                           fileauthor=fileauthor)
    fileid = libdb.add_file(bookfile)
    fileid = str(fileid)
    bookfile.id = fileid
    libdb.edit_book_add_file(bookid, fileid)
    # проверка дублей (TODO: возвращать и выводить на странице добавления)
    dups = libdb.check_dups(bookfile, bookid)
    # переводчики (принадлежат файлам, а не книгам)
    trans = set()
    for author in alltranslators:
        # проверяем наличие переводчиков
        transids = libdb.find_author(author)
        if not transids:
            # автор не найден - добавляем нового автора
            aid = libdb.add_author(author)
            trans.add(aid)
        else:
            trans.update(transids)
    for authorid in trans:
        # добавляем связь книга<->переводчик
        libdb.edit_book_add_translator(bookid, authorid)
    # добавляем издательские серии
    for seq in allpublsequences:
        try:
            libdb.add_sequence(bookid, seq[0], seq[1], True)
        except libdb.DBError:
            pass
    # переносим файл в нужный каталог
    dir = os.path.join(books_dir, fileid)
    makedir(fileid)
    to = os.path.join(dir, fileid+'.fb2')
    shutil.move(fn, to)
    # иллюстрации/обложки
    save_binaries(xml, dir, fileid)
    if generate_when_adding:
        # записываем txt
        to = os.path.join(dir, fileid+'.txt')
        open(to, 'w').write(txt)
        # создаём и записываем html
        to = os.path.join(dir, fileid+'.html')
        plugins.fb2_to_html(to, xml=xml)
    # аннотация
    save_annotation(xml, bookid, fileid)
    # fb2 description
    save_description(xml, fileid)
    # сохраняем ошибки валидации
    libdb.save_fb2_errors(fileid, errors)
    # сбрасываем флаг needupdate
    libdb.reset_need_update(fileid)
    session.hide_username = False
    return bookid, fileid, newbook

def add_other_file(f, bookid):
    session.hide_username = True
    # md5
    md5digest = get_md5(f.filename)
    # filesize
    filesize = os.path.getsize(f.filename)
    ext = os.path.splitext(f.origname)[1]
    book = libdb.get_book_info(bookid)
    # записываем инф-цию о файле в db
    bookfile = dict(title=book.title, md5=md5digest, filetype=f.filetype,
                    filesize=filesize, textsize=filesize, origext=ext)
    fileid = libdb.add_file(bookfile)
    libdb.edit_book_add_file(bookid, fileid)
    # переносим файл в нужный каталог
    makedir(fileid)
    dir = os.path.join(books_dir, str(fileid))
    to = os.path.join(dir, str(fileid)+ext)
    shutil.move(f.filename, to)
    session.hide_username = False
    return fileid

def add_book(title, allauthors, allgenres=[], allsequences=[], **book):
    ''' поиск соответствующей книги
    если книга не найдена - добавляем ее в базу
    также добавляем в базу новых авторов
    возвращаем bookid и флаг - создана/не создана новая книга'''
    bookid = None
    authors = set()
    for author in allauthors:
        # проверяем наличие авторов
        authorids = libdb.find_author(author)
        if not authorids:
            # автор не найден - добавляем нового автора
            aid = libdb.add_author(author)
            authors.add(aid)
            continue
        # если такой автор уже есть - проверяем наличие книги
        # по комбинации (title, authorid)
        for aid in authorids:
            authors.add(aid)
            if bookid is None:
                # если книга еще не найдена - ищем
                books = libdb.find_book(title, aid)
                #if len(books) > 1:
                #    print 'DB consistention error'
                if books:
                    # найдена нужная книга
                    bookid = books[0]
    newbook = bookid is None
    if newbook:
        # создаем новую книгу
        book['title'] = title
        bookid = libdb.add_book(book)
        for authorid in authors:
            # добавляем связь книга<->автор
            libdb.edit_book_add_author(bookid, authorid)
        # добавляем жанры
        total = 0
        for gen in allgenres:
            if libdb.add_gen(bookid, gen):
                total += 1
        if total == 0:
            # не добавлен ни один жанр - добавляем other
            libdb.add_gen(bookid, 'other')
        # сериал
        for seq in allsequences:
            try:
                libdb.add_sequence(bookid, seq[0], seq[1])
            except libdb.DBError:
                pass
    return bookid, newbook


if __name__ == '__main__':
    session = web.Storage()
    print add_fb2_file(sys.argv[1], [])

