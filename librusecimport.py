#!/usr/bin/env python
# -*- mode: python; coding: utf-8; -*-
# (c) Lankier mailto:lankier@gmail.com
import sys, os
from hashlib import md5
import web

from brigantina import addfile, validator, libdb, utils
from fb2utils import parser             # http://code.google.com/p/fb2utils/

src_dir = 'fb2'
dest_dir = 'files'
fixed_dir = 'fixed'

pgdb = web.database(dbn='postgres', db='library', user='con', pw='')
mydb = web.database(dbn='mysql', db='rate', user='www', pw='a1s2d3')

## -- временные индексы для импорта
def create_indexes():
    pgdb.query('''\
create index files_librusecid_index on files (librusecid);
create index authors_librusecid_index on authors (librusecid);
create index authorsaliases_librusecid_index on authorsaliases (librusecid);
create index sequences_librusecid_index on sequences (librusecid);
create index publsequences_librusecid_index on publsequences (librusecid);''')

## -- удаление временных индексов (после импорта)
def drop_indexes():
    pgdb.query('''\
drop index if exists files_librusecid_index cascade;
drop index if exists authors_librusecid_index cascade;
drop index if exists authorsaliases_librusecid_index cascade;
drop index if exists sequences_librusecid_index cascade;
drop index if exists publsequences_librusecid_index cascade;''')

def print_log(*s):
    s = ' '.join(str(i) for i in s)
    if isinstance(s, unicode):
        s = s.encode('utf-8')
    print s
    sys.stdout.flush()

def import_authors():
    nauthors = 0
    for author in mydb.select('libavtorname'):
        if 0:
            try:
                pgdb.select('authors', locals(),
                            where='librusecid=$author.AvtorId')[0]
            except IndexError:
                pass
            else:
                continue
        try:
            mydb.select('libavtoraliase', locals(),
                        where='BadId=$author.AvtorId')[0]
        except IndexError:
            pass
        else:
            # удалён
            continue
        if not author.FirstName and not author.LastName:
            # безымянные авторы
            continue
        nbooks = 0
        nbooks += mydb.select('libavtor', locals(), what='count(*) as count',
                              where='AvtorId = $author.AvtorId')[0].count
        nbooks += mydb.select('libtranslator', locals(), what='count(*) as count',
                              where='TranslatorId = $author.AvtorId')[0].count
        if nbooks == 0:
            # нет книг
            print_log('skip author:', author.AvtorId)
            continue
        newid = pgdb.insert('authors',
                            firstname=author.FirstName,
                            middlename=author.MiddleName,
                            lastname=author.LastName,
                            nickname=author.NickName,
                            librusecid=author.AvtorId)
        for alias in mydb.select('libavtoraliase', locals(),
                                 where='GoodId=$author.AvtorId'):
            # другие имена
            try:
                a = mydb.select('libavtorname', locals(),
                                where='AvtorId=$alias.BadId')[0]
            except IndexError:
                continue
            pgdb.insert('authorsaliases', False, authorid=newid,
                        firstname=a.FirstName, middlename=a.MiddleName,
                        lastname=a.LastName, nickname=a.NickName,
                        librusecid=a.AvtorId)
        nauthors += 1
    print 'total', nauthors, 'added'

def get_author(aid):
    # поиск автора по алиасу
    try:
        res = mydb.select('libavtoraliase', locals(), where='BadId=$aid')[0]
    except IndexError:
        return None
    try:
        res = pgdb.select('authors', locals(), where='librusecid=$res.GoodId')[0]
    except IndexError:
        return None
    return res.id

xpath_prefix = '/m:FictionBook/m:description/m:title-info'

def import_books():
    nbooks = 0
    nfiles = 0
    for book in mydb.select('libbook'):
        if book.Deleted == '1':
            continue
        if book.FileSize >= 2147483647:
            # 2 GB (см. http://www.flibusta.net/b/170630)
            print_log('too large:', book.BookId)
            continue
        if 0:
            # продолжение после предыдущей ошибки
            try:
                pgdb.select('files', locals(), where='librusecid=$book.BookId')[0]
            except IndexError:
                pass
            else:
                # этот файл уже обработан
                print_log('already exists:', book.BookId)
                continue
        if book.FileType == 'fb2':
            fn = str(book.BookId)+'.fb2'
        else:
            try:
                fn = mydb.select('libfilename', locals(),
                                 where='BookId=$book.BookId')[0].FileName
            except IndexError:
                print_log('filename not found:', book.BookId)
                continue
        fn = os.path.join(src_dir, fn)
        if book.FileType == 'fb2':
            if not os.path.exists(fn):
                print_log('not exists:', fn)
                continue
        soup = None
        errors = []
        if book.FileType == 'fb2':
            xml = validator.check_file(fn, errors)
            if not xml:
                print_log('bad xml:', fn)
                #continue
                # исправляем xml
                data = open(fn).read()
                soup = parser.FB2Parser(data, convertEntities='xml')
                xml = validator.check_str(str(soup.FictionBook), errors)
                assert xml is not None
        authors = set()                 # список id авторов
        bookid  = None                  # в какую книгу добавляем файл
        alttitles = []
        if book.Title1.startswith('='):
            t1 = book.Title1[1:].strip()
            alttitles = t1.split(';')
            book.Title1 = ''
        for a in mydb.select('libavtor', locals(), where='BookId=$book.BookId'):
            try:
                author = pgdb.select('authors', locals(),
                                     where='librusecid=$a.AvtorId')[0]
            except IndexError:
                aid = get_author(a.AvtorId)
                if not aid:
                    # иногда встречаются удалённые авторы
                    print_log('author not found:', book.BookId, a.AvtorId)
                    continue
            else:
                aid = author.id
            authors.add(aid)
            if not bookid:
                books = libdb.find_book(book.Title, aid)
                if books:
                    # найдена подходящая книга
                    bookid = books[0]
                else:
                    for t in alttitles:
                        books = libdb.find_book(t, aid)
                        if books:
                            # найдена подходящая книга
                            bookid = books[0]
                            break
        if not authors:
            a = pgdb.select('authors', where="lastname='Автор неизвестен'")[0]
            authors =[a.id]
        assert authors                  # должен быть хотя бы один
        if not bookid:
            # создаём новую книгу
            if book.FileType == 'fb2':
                year = addfile.get_year(xml)
                lang = addfile.get_elem(xml, xpath_prefix, 'src-lang')
                bookid = pgdb.insert('books', year=year, lang=lang,
                                     title=book.Title)
            else:
                bookid = pgdb.insert('books', title=book.Title)
            # связываем с авторами
            for aid in authors:
                pgdb.insert('booksauthors', False, bookid=bookid, authorid=aid)
            # жанры
            genadded = False
            for g in mydb.select('libgenre', locals(),
                                 where='BookId=$book.BookId'):
                genreid = mydb.select('libgenrelist', locals(),
                                      where='GenreId=$g.GenreId')[0].GenreCode
                #pgdb.select('genres', locals(), where='id=$genreid')[0]
                pgdb.insert('booksgenres', False, bookid=bookid, genreid=genreid)
                genadded = True
            if not genadded:
                # если не добавлен ни один жанр
                pgdb.insert('booksgenres', False, bookid=bookid, genreid='other')
            #print_log('book added:', bookid)
            for t in alttitles:
                try:
                    libdb.edit_book_add_alttitle(bookid, t.strip())
                except libdb.DBError:
                    pass
            nbooks += 1
        # заголовок файла
        if book.Title1:
            title = book.Title1
        else:
            title = book.Title
        #
        if book.FileType == 'fb2':
            txt = utils.fb2txt(xml)
            textsize = len(txt)
            fb2id = addfile.get_elem(xml, '/m:FictionBook/m:description/m:document-info', 'id')
            v = addfile.get_elem(xml, '/m:FictionBook/m:description/m:document-info', 'version')
            try:
                fb2version = float(v)
            except:
                fb2version = None
            ext = None
        else:
            textsize = book.FileSize
            fb2id = None
            fb2version = None
            ext = os.path.splitext(fn)[1]
        #
        fileid = pgdb.insert('files', title=title,
                             lang=book.Lang, year=book.Year,
                             filetype=book.FileType,
                             fileauthor=book.FileAuthor,
                             filesize=book.FileSize, origext=ext,
                             textsize=textsize, md5=book.md5,
                             fb2id=fb2id, fb2version=fb2version,
                             librusecid=book.BookId)
        fileid = str(fileid)
        #print_log('file added:', fileid)
        nfiles += 1
        # сохраняем исправленный файл
        if book.FileType == 'fb2' and soup:
            f = os.path.join(fixed_dir, fileid)
            open(f, 'w').write(str(soup.FictionBook))
        # связь книга<->файл
        pgdb.insert('booksfiles', False, bookid=bookid, fileid=fileid)
        # переводчики
        translators = set()
        for trans in mydb.select('libtranslator', locals(),
                                 where='BookId=$book.BookId'):
            try:
                transid = pgdb.select('authors', locals(),
                                      where='librusecid=$trans.TranslatorId')[0]
            except IndexError:
                transid = get_author(trans.TranslatorId)
                if not transid:
                    print_log('translator not found:', book.BookId, trans.TranslatorId)
                    continue
            else:
                transid = transid.id
            if transid in translators:
                continue
            translators.add(transid)
            pgdb.insert('bookstranslators', fileid=fileid, authorid=transid)
        # сериалы
        for seq in mydb.select('libseq', locals(), where='BookId=$book.BookId'):
            seqname = mydb.select('libseqname', locals(),
                                  where='SeqId=$seq.SeqId')[0].SeqName
            if seq.Level >= 100:
                # издательский сериал
                try:
                    seqid = pgdb.select('publsequences', locals(),
                                        where='librusecid=$seq.SeqId')[0].id
                except IndexError:
                    seqid = pgdb.insert('publsequences', name=seqname,
                                        librusecid=seq.SeqId)
                pgdb.insert('filessequences', False, fileid=fileid,
                            sequenceid=seqid, sequencenumber=seq.SeqNumb)
            else:
                # авторский
                try:
                    seqid = pgdb.select('sequences', locals(),
                                        where='librusecid=$seq.SeqId')[0].id
                except IndexError:
                    seqid = pgdb.insert('sequences', name=seqname,
                                        librusecid=seq.SeqId)
                try:
                    # возможно эта книга уже была засериализована другим файлом
                    pgdb.select('bookssequences', locals(),
                                where='bookid=$bookid and sequenceid=$seqid')[0]
                except IndexError:
                    pgdb.insert('bookssequences', False, bookid=bookid,
                                sequenceid=seqid, sequencenumber=seq.SeqNumb)
        if book.FileType == 'fb2':
            # description
            addfile.save_description(xml, fileid)
            # annotation
            addfile.save_annotation(xml, bookid, fileid)
            # errors
            libdb.save_fb2_errors(fileid, errors)
            # covers
            utils.makedir(fileid)
            dir = os.path.join(dest_dir, fileid)
            addfile.save_binaries(xml, dir, fileid)
            # сохранение в других форматах
            # txt
            # html
        # перемещение/копирование/ссылка файла

    print_log(nbooks, 'books and', nfiles, 'files was imported')

def import_reviews():
    for review in mydb.select('libreviews'):
        print review.Text.encode('utf-8').replace('\\n', '\n').replace('\n', '\n\n').strip()
        print '-'*70

def cleanup():
    pgdb.delete('actions')

def get_md5(fn):
    m = md5()
    fd = open(fn)
    while True:
        s = fd.read(1024)
        if not s:
            break
        m.update(s)
    md5digest = m.hexdigest()
    return md5digest

def check_files():
    for book in mydb.select('libbook'):
        if book.Deleted == '1':
            continue
        if book.FileType != 'fb2':
            continue
        fn = str(book.BookId)+'.fb2'
        fn = os.path.join(src_dir, fn)
        if not os.path.exists(fn):
            print_log('not exists:', fn)
            continue
        md5digest = get_md5(fn)
        if md5digest != book.md5:
            print_log('md5 fail:', fn)
            continue
        #print_log('ok:', fn)

#create_indexes()
#check_files()
#import_authors()
#import_books()
import_reviews()
#drop_indexes()
#cleanup()

