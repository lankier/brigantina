#!/usr/bin/env python
# -*- mode: python; coding: utf-8; -*-
# (c) Lankier mailto:lankier@gmail.com
import sys, os
try:
    import cPickle as pickle
except ImportError:
    import pickle
import datetime
import web
safestr = web.utils.safestr

from config import db_args
from utils import annotation2html, authorname

_db = web.database(**db_args)

class DBError(Exception):
    pass

def db_log(action, oldvalue=None, strvalue=None, needupdate=False, **kwargs):
    #print web.config._session.username, action, kwargs
    try:
        username = web.config._session.username
    except:
        username = 'bot'
    try:
        hide_username = session.hide_username
    except:
        hide_username = False
    d = {
        'authorid': (u'автор', '/author/', 'authors',
                     ('firstname', 'middlename', 'lastname')),
        'bookid': (u'книга', '/book/', 'books', 'title'),
        'fileid': (u'файл', '/file/', 'files', 'title'),
        'sequenceid': (u'сериал', '/sequence/', 'sequences', 'name'),
        'publsequenceid': (u'серия', '/publsequence/', 'publsequences', 'name'),
        'genreid': (u'жанр', '/genre/', 'genres', 'description'),
        }
    pages = []
    for idname in kwargs:
        desc, url, table, what = d[idname]
        try:
            res = _db.select(table, kwargs, where=('id = $%s' % idname))[0]
        except IndexError:
            #
            continue
        if isinstance(what, tuple):
            title = ' '.join(res[w] for w in what)
        else:
            title = res[what]
        url = url+str(res.id)
        p = ' '.join((desc, url, str(res.id), title))
        pages.append(p)
    pages = '\n'.join(pages)
    kwargs['action'] = action
    kwargs['username'] = username
    kwargs['pages'] = pages
    kwargs['hideusername'] = hide_username
    if oldvalue:
        kwargs['valuechanged'] = True
    id = _db.insert('actions', **kwargs)
    if oldvalue:
        if strvalue:
            # если сохраняется объект
            oldvalue = pickle.dumps(oldvalue)
            _db.insert('oldvalues', False, actionid=id, dumped=True,
                       body=oldvalue, str=strvalue)
        else:
            # если сохраняется строка
            _db.insert('oldvalues', False, actionid=id, body=oldvalue)
    # помечаем, если требуется синхронизация
    if not needupdate:
        return
    bookid = kwargs.get('bookid')
    fileid = kwargs.get('fileid')
    authorid = kwargs.get('authorid')
    sequenceid =  kwargs.get('sequenceid')
    publsequenceid =  kwargs.get('publsequenceid')
    files = set()                      # список id файлов требующих обновления
    def _add_files(bookid):
        for f in _db.select('booksfiles', locals(), what='fileid',
                            where='bookid = $bookid'):
            files.add(f.fileid)
    if fileid:
        files.add(fileid)
    if bookid:
        _add_files(bookid)
    # если автор - помечаем все его книги
    if authorid:
        for r in _db.select('booksauthors', locals(),
                            where='authorid = $authorid'):
            _add_files(r.bookid)
        for r in _db.select('bookstranslators', locals(),
                            where='authorid = $authorid'):
            _add_files(r.bookid)
    # все книги сериала
    if sequenceid:
        for r in _db.select('bookssequences', locals(),
                            where='sequenceid = $sequenceid'):
            _add_files(r.bookid)
    # изд. серии
    if publsequenceid:
        for r in _db.select('bookspublsequences', locals(),
                            where='sequenceid = $sequenceid'):
            _add_files(r.bookid)
    # помечаем все затронутые файлы
    for f in files:
        _db.update('files', vars=locals(), needupdate=True, where='id = $f')

def reset_need_update(fileid):
    '''сбросить флаг needupdate'''
    _db.update('files', vars=locals(), needupdate=False, where='id = $fileid')

def undo(actionid):
    undo_actions = {
        # ключ: описание действия
        # значение: список из двух элементов
        # первый - функция, которая используется для отката
        # второй - аргументы функци (извлекаются из таблиц action и oldvalues)
        # берутся значения этих столбцов и к ним добавляется oldvalue
        # если аргумент - словарь, то используется func(**args)
        u'изменена аннотация книги': (
            update_book_ann, ['bookid']),
        u'изменена аннотация файла': (
            update_file_ann, ['fileid']),
        u'изменено название книги': (
            edit_book_set_title, ['bookid']),
        u'изменена форма книги': (
            edit_book_set_form, ['bookid']),
        u'изменён год написания книги': (
            edit_book_set_year, ['bookid']),
        u'изменён язык книги': (
            edit_book_set_lang, ['bookid']),
        u'изменён год издания': (
            edit_book_set_publ_year, ['bookid']),
        u'изменён язык издания': (
            edit_book_set_publ_lang, ['bookid']),
        u'из книги удалено альтернативное название': (
            edit_book_add_alttitle, ['bookid']),
        u'изменено название сериала': (
            edit_sequence_set_name, ['sequenceid']),
        u'у книги изменён порядковый номер в сериале': (
            edit_sequence_set_number, ['sequenceid', 'bookid']),
        u'изменён заголовок файла': (
            edit_file_set_title, ['fileid']),
        u'у автора изменено имя': (
            edit_author_set_name, {'authorid': None, 'firstname': 'oldvalue'}),
        u'у автора изменено отчество': (
            edit_author_set_name, {'authorid': None, 'middlename': 'oldvalue'}),
        u'у автора изменена фамилия': (
            edit_author_set_name, {'authorid': None, 'lastname': 'oldvalue'}),
        u'у автора изменён псевдоним': (
            edit_author_set_name, {'authorid': None, 'nickname': 'oldvalue'}),
        u'изменена биография автора': (
            edit_author_set_biography, ['authorid']),
        u'у автора удалён алиас': (
            edit_author_add_alias, ['authorid']),
        u'из книги удалён жанр': (
            edit_book_add_genre, ['bookid']),
        u'из книги удалён автор': (
            edit_book_add_author, ['bookid']),
        u'из книги удалён переводчик': (
            edit_book_add_translator, ['bookid']),
        u'из книги удалён файл': (
            edit_book_add_file, ['bookid']),
        u'из книги удалён сериал': (
            edit_book_add_sequence, ['bookid', 'sequenceid']),
        u'из книги удалена издательская серия': (
            edit_book_add_publ_sequence, ['bookid', 'publsequenceid']),
        }
    try:
        res = _db.select('actions', locals(), where='id = $actionid')[0]
    except IndexError:
        return False
    try:
        do = undo_actions[res.action]
    except:
        return False
    try:
        oldvalue = _db.select('oldvalues', locals(),
                              where='actionid = $actionid')[0]
    except IndexError:
        return False
    if oldvalue.dumped:
        # объект - распаковываем
        oldvalue = pickle.loads(safestr(oldvalue.body))
    else:
        # строка - используем как есть
        oldvalue = oldvalue.body
    func = do[0]
    if isinstance(do[1], list):
        args = []
        for a in do[1]:
            args.append(res[a])
        args.append(oldvalue)
        func(*args)
    elif isinstance(do[1], dict):
        args = {}
        v = do[1]
        for a in v:
            if v[a] is None:
                args[a] = res[a]
            elif v[a] == 'oldvalue':
                args[a] = oldvalue
            else:
                args[a] = v[a]
        func(**args)
    return True

def _paging_select(select, query, order, page, limit, vars=None):
    '''функция для работы с постраничными списками
    запрос разбит на три части:
      select - select что-то
      query - from откуда
      order - order by как
    page - номер запрашиваемой страницы
    limit - количество строк на странице
    vars - доп. аргументы
    возвращает количество страниц, сколько всего строк и результат выборки'''
    count = _db.query('select count(*) ' + query, vars=vars)[0].count
    numpages = (count - 1) / limit
    if page is None:
        offset = ''
    else:
        offset = ' offset ' + str(page * limit)
    q = ' '.join((select, query, order, offset, 'limit', str(limit)))
    res = list(_db.query(q, vars=vars))
    return numpages, count, res

## ----------------------------------------------------------------------
## ф-ции для добавления файла (addfile.py)
## ----------------------------------------------------------------------

def check_file(md5):
    '''проверка существования файла по md5 (для upload)
    возвращает True если такого файла нет
    иначе - False'''
    try:
        _db.select('files', locals(), what='id', where='md5 = $md5')[0]
    except IndexError:
        return True
    return False

def check_dups(file, bookid=None):
    '''проверка дублей
    прячет найденые файлы с таким же fb2 id и меньшей версией'''
    hf = []                         # список id файлов, которые будут спрятаны
    if (bookid and file.filetype == 'fb2' and
        'fb2id' in file and 'fb2version' in file):
        res = list(_db.query(
            'select files.* from files, booksfiles '
            'where files.id = booksfiles.fileid '
            'and booksfiles.bookid = $bookid and files.fb2id = $fb2id',
            vars=dict(bookid=bookid, fb2id=file['fb2id'])))
        for f in res:
            if f.fb2version < file.fb2version:
                edit_book_hide_file(bookid, f.id, 'hide')
                hf.append(f.id)
    return hf

def find_author(author, addaliases=True):
    '''поиск автора по имени, возвращает список authorid'''
    var = {}
    where = ''
    for n in ('firstname', 'middlename', 'lastname'):
        # проверяем совпадение всех трёх имён, даже если какие-то пустые
        # (чтобы отличать Василий А Пупкин от Василий Б Пупкин)
        var[n] = author.get(n, '')
        if where: where += ' and '
        where += 'lower(%s) = lower($%s)' % (n, n)
    result = _db.select('authors', var, what='id', where=where)
    result = set([i.id for i in result])
    if addaliases:
        # поиск среди псевдонимов
        aliases = _db.select('authorsaliases', var, what='authorid', where=where)
        result.update([i.authorid for i in aliases])
    return result

def find_book(title, authorid):
    '''проверка существование книги с таким автором'''
    bookid = _db.select('books', locals(), what='id',
                        where='lower(title) = lower($title)')
    bookid = [i.id for i in bookid]
    if not bookid:
        # книга с таким title не найдена
        return None
    # проверяем вместе с автором
    allbooks = []
    for b in bookid:
        try:
            _db.select('booksauthors', locals(),
                       where='bookid = $b and authorid = $authorid')[0]
        except IndexError:
            continue
        allbooks.append(b)
    return allbooks

def add_author(author):
    # возвращает id добавленного автора
    authorid = _db.insert('authors', **author)
    db_log(u'в библиотеку добавлен автор', authorid=authorid)
    return authorid

def add_book(book):
    # возвращает id добавленной книги
    bookid = _db.insert('books', **book)
    db_log(u'в библиотеку добавлена книга', bookid=bookid)
    return bookid

def add_file(file):
    # возвращает id добавленного файла
    fileid = _db.insert('files', **file)
    db_log(u'в библиотеку добавлен файл', fileid=fileid)
    return fileid

def add_gen(bookid, genreid):
    '''добавляет в книгу жанр'''
    try:
        # есть ли такой жанр?
        _db.select('genres', locals(), where='id = $genreid')[0]
    except IndexError:
        # нет такого жанра
        # попробуем поискать в списке старых жанров
        res  = _db.select('oldgenres', locals(), where='oldid = $genreid')
        try:
           genreid = res[0].newid
        except IndexError:
            # не нашли - уходим
            return False
        # нашли - заменяем
    _db.insert('booksgenres', False, genreid=genreid, bookid=bookid)
    db_log(u'в книгу добавлен жанр', genreid=genreid, bookid=bookid,
           needupdate=True)
    return True

def add_sequence(itemid, sequencename, sequencenumber, publish=False):
    '''создать сериал если его еще нет
    добавить связь bookid<->(sequenceid, sequencenumber)'''
    sequencename = ' '.join(sequencename.split())
    if not sequencenumber:
        sequencenumber = 0
    try:
        sequencenumber = int(sequencenumber)
    except:
        raise DBError(u'Неправильный номер сериала')
    if publish:
        # издательская серия
        sequencetable = 'publsequences'
        relattable = 'bookspublsequences'
        where = ('bookid = $itemid and sequenceid = $sequenceid and '
                 'sequencenumber = $sequencenumber')
        check_where = 'bookid = $itemid and sequenceid = $sequenceid'
    else:
        # авторский сериал
        sequencetable = 'sequences'
        relattable = 'bookssequences'
        where = ('bookid = $itemid and sequenceid = $sequenceid and '
                 'sequencenumber = $sequencenumber')
        check_where = 'bookid = $itemid and sequenceid = $sequenceid'
    newseq = False
    try:
        sequence = _db.select(sequencetable, locals(),
                              where='name = $sequencename')[0]
    except IndexError:
        # сериал не найден - создаем
        sequenceid = _db.insert(sequencetable, name=sequencename)
        newseq = True
        if publish:
            db_log(u'создана новая серия', publsequenceid=sequenceid)
        else:
            db_log(u'создан новый сериал', sequenceid=sequenceid)
    else:
        # найден нужный сериал
        sequenceid = sequence.id
    try:
        _db.select(relattable, locals(), where=check_where)[0]
    except IndexError:
        pass
    else:
        # существует запись (bookid, sequenceid)
        raise DBError(u'Сериал уже добавлен.')
    _db.insert(relattable, False, bookid=itemid,
               sequenceid=sequenceid, sequencenumber=sequencenumber)
    if publish:
        db_log(u'в книгу добавлена издательская серия', publsequenceid=sequenceid,
               bookid=itemid, needupdate=True)
    else:
        db_log(u'в книгу добавлен сериал', sequenceid=sequenceid,
               bookid=itemid, needupdate=True)
    return (sequenceid, newseq)

def add_images(fileid, images, covers):
    images = pickle.dumps(images)
    covers = pickle.dumps(covers)
    _db.update('files', vars=locals(), images=images, covers=covers,
               where='id = $fileid')

def _add_ann(table, id, ann, html, force=False):
    old = False
    res = _db.select(table, locals(), where='id = $id')[0]
    if res.annotation and force:
        # обновление
        old = res.annotation
        _db.update(table, where='id = $id', annotation=ann, annotation_html=html,
                   vars=locals())
    elif not res.annotation:
        # аннотация отсутствует
        _db.update(table, where='id = $id', annotation=ann, annotation_html=html,
                   vars=locals())
    if old:
        if table == 'books':
            db_log(u'изменена аннотация книги', needupdate=True, oldvalue=old,
                   bookid=id)
        else:
            db_log(u'изменена аннотация файла', needupdate=True, oldvalue=old,
                   fileid=id)
    else:
        if table == 'books':
            db_log(u'добавлена аннотация к книге', needupdate=True, bookid=id)
        else:
            db_log(u'добавлена аннотация к файлу', needupdate=True, fileid=id)

def add_book_desc(bookid, fileid, ann, html):
    '''добавление аннотации'''
    _add_ann('books', bookid, ann, html)
    _add_ann('files', fileid, ann, html)

def update_book_ann(bookid, ann, html=None):
    '''обновление аннотации книги'''
    if html is None:
        html = annotation2html(ann)
    _add_ann('books', bookid, ann, html, force=True)

def update_file_ann(fileid, ann, html=None):
    '''обновление аннотации файла'''
    if html is None:
        html = annotation2html(ann)
    _add_ann('files', fileid, ann, html, force=True)

def save_file_description(fileid, desc):
    '''сохранение fb2 description'''
    _db.update('files', vars=locals(), where='id = $fileid', description=desc)

## ----------------------------------------------------------------------
## ф-ции для page.py
## ----------------------------------------------------------------------

def book_get_ann(bookid, column='annotation_html'):
    ann = _db.select('books', locals(), where='id = $bookid',
                     what=column)[0][column]
    if not ann:
        ann = ''
    return ann

def add_authors_to_book(item, table='booksauthors', limit=None):
    '''добавляет список авторов или переводчиков к книге'''
    query = ('select authors.* from %(table)s, authors '
             'where %(table)s.authorid = authors.id '
             'and %(table)s.bookid = $item.id' % locals())
    if limit is not None:
        query += (' limit %d' % limit)
    authors = list(_db.query(query, vars=locals()))
    if table == 'booksauthors':
        item.authors = authors
    else:
        item.translators = authors

def add_files_to_book(book, hidden=True):
    if hidden:
        # добавлять все файлы
        where = ''
    else:
        # добавлять только не спрятанные
        where = ' and not booksfiles.hidden'
    files = list(_db.query('select files.*, booksfiles.hidden '
                           'from booksfiles, files '
                           'where booksfiles.fileid = files.id '
                           'and booksfiles.bookid = $book.id'''+where,
                           vars=locals()))
    book.files = files
    add_authors_to_book(book, 'bookstranslators')
    for f in files:
        f.filetype = f.filetype.strip()

def add_genres_to_book(book):
    genres = list(_db.query('select genres.* from booksgenres, genres '
                            'where booksgenres.genreid = genres.id '
                            'and booksgenres.bookid = $book.id', vars=locals()))
    book.genres = genres

def add_sequences_to_book(item, table='bookssequences', seqtable='sequences'):
    '''добавляет сериалы к книге или файлу'''
    query = ('select %(seqtable)s.name, %(seqtable)s.id, '
             '%(table)s.sequencenumber as number '
             'from %(table)s, %(seqtable)s '
             'where %(table)s.sequenceid = %(seqtable)s.id '
             'and %(table)s.bookid = $item.id' % locals())
    sequences = list(_db.query(query, vars=locals()))
    item[seqtable] = sequences

def add_alttitles_to_book(book):
    alttitles = list(_db.select('alttitles', locals(), where='bookid = $book.id'))
    book.alttitles = alttitles

def get_book(bookid, add_hidden_files=False):
    try:
        book = _db.select('books', locals(), where='id = $bookid')[0]
    except IndexError:
        return False
    # авторы
    add_authors_to_book(book)
    # файлы
    add_files_to_book(book, hidden=add_hidden_files)
    # аннотация
    if 'annotation_html' in book:
        book.annotation = book.annotation_html
    else:
        book.annotation = ''
    # добавляем обложки
    if 'covers' in book and book.covers:
        book.covers = pickle.loads(safestr(book.covers))
    else:
        book.covers = []
    for f in book.files:
        # обложки файлов
        if f.covers:
            for c in pickle.loads(safestr(f.covers)):
                cover = web.Storage(fileid=f.id, filename=c)
                book.covers.append(cover)
    # добавляем переводчиков
    add_authors_to_book(book, 'bookstranslators')
    # другие имена
    add_alttitles_to_book(book)
    # жанры
    add_genres_to_book(book)
    # авторские сериалы
    add_sequences_to_book(book)
    # изд. серии
    add_sequences_to_book(book, 'bookspublsequences', 'publsequences')
    return book

def get_book_info(bookid):
    try:
        book = _db.select('books', locals(), where='id = $bookid')[0]
    except IndexError:
        raise DBError(u'Такой книги не существует')
    return book

## ----------------------------------------------------------------------

def add_books_to_author(author, sort_by='sequence'):
    if sort_by == 'sequence':
        query = (
            'select '
            'sequences.id as sequenceid, '
            'sequences.name as sequencename, '
            'sequences.parrent as sequenceparrent, '
            'bookssequences.sequencenumber as sequencenumber, '
            'books.* '
            'from booksauthors '
            'inner join books on (booksauthors.bookid = books.id) '
            'left join bookssequences on (books.id = bookssequences.bookid) '
            'left join sequences on (bookssequences.sequenceid = sequences.id) '
            'where booksauthors.authorid = $author.id and not books.deleted '
            'order by sequenceparrent, sequencename, sequencenumber, books.title')
    else:
        query = ('select books.* from booksauthors, books '
                 'where booksauthors.bookid = books.id '
                 'and booksauthors.authorid = $author.id')
    books = list(_db.query(query, vars=locals()))
    bookslist = []
    for b in books:
##         if sort_by == 'sequence':
##             # добавляем инф-цию о родительском сериале
##             if b.sequenceparrent:
##                 try:
##                     sequence = _db.select('sequences', locals(),
##                                           where='id = $b.sequenceparrent')[0]
##                 except IndexError:
##                     b.sequenceparrent = None
##                 else:
##                     b.sequenceparrent = sequence
        # жанры
        add_genres_to_book(b)
        add_files_to_book(b)
    author.books = books

def get_author(authorid, sort_by='sequence', add_books=True, add_biography=True):
    try:
        author = _db.select('authors', locals(), where='id = $authorid')[0]
    except IndexError:
        return False
    if add_books:
        add_books_to_author(author)
    if add_biography:
        try:
            res = _db.select('authorsdesc', locals(),
                             where='authorid = $authorid')[0]
        except IndexError:
            author.biography = ''
        else:
            author.biography = res.body
    aliases = _db.select('authorsaliases', locals(), where='authorid = $authorid')
    author.aliases = aliases
    return author

def get_author_info(authorid):
    try:
        author = _db.select('authors', locals(), where='id = $authorid')[0]
    except IndexError:
        raise DBError(u'Такого автора не существует')
    return author

def add_books_to_sequence(sequence):
    query = ('select books.*, '
             'bookssequences.sequencenumber, '
             'bookssequences.sequenceid '
             'from bookssequences, books '
             'where bookssequences.bookid = books.id '
             'and bookssequences.sequenceid = $sequence.id '
             'order by bookssequences.sequencenumber')
    books = list(_db.query(query, vars=locals()))
    for b in books:
        add_authors_to_book(b, limit=1)
        add_files_to_book(b)
    sequence.books = books

def get_sequence(sequenceid):
    try:
        sequence = _db.select('sequences', locals(), where='id = $sequenceid')[0]
    except IndexError:
        return False
    add_books_to_sequence(sequence)
    if sequence.parrent:
        try:
            par = _db.select('sequences', locals(),
                             where='id = $sequence.parrent')[0]
        except IndexError:
            sequence.parrent = None
        else:
            sequence.parrent = par
    return sequence

def get_genre(genreid, page, limit=100):
    try:
        genre = _db.select('genres', locals(), where='id = $genreid')[0]
    except IndexError:
        return False, False, False
    numpages, count, books = _paging_select(
        'select books.*', 'from books, booksgenres '
        'where books.id = booksgenres.bookid '
        'and booksgenres.genreid = $genreid', 'order by books.title',
        page, limit, locals())
    for b in books:
        add_authors_to_book(b, limit=1)
        add_files_to_book(b)
    genre.books = books
    return genre, numpages, count

def get_all_genres():
    genres = {}
    res = _db.select('genres', order='description')
    for g in res:
        if g.metagenre in genres:
            genres[g.metagenre].append((g.id, g.description))
        else:
            genres[g.metagenre] = [(g.id, g.description)]
    genreslist = genres.items()
    genreslist.sort()
    return genreslist

## ----------------------------------------------------------------------

def add_books_to_file(file):
    query = ('select books.* from booksfiles, books '
             'where booksfiles.bookid = books.id '
             'and booksfiles.fileid = $file.id')
    books = list(_db.query(query, vars=locals()))
    for b in books:
        add_authors_to_book(b, limit=1)
    file.books = books

def get_file(fileid):
    try:
        file = _db.select('files', locals(), where='id = $fileid')[0]
    except IndexError:
        return False
    file.filetype = file.filetype.strip()
    add_books_to_file(file)
    if file.filetype == 'fb2':
        file.desc = file.description
        try:
            res = _db.select('fb2errors', locals(), where='fileid = $fileid')[0]
        except:
            file.errors = 0
        else:
            file.errors = res.errors
            file.numerrors = res.numerrors
            file.numwarnings = res.numwarnings
    return file

def get_file_info(fileid):
    try:
        file = _db.select('files', locals(), where='id = $fileid')[0]
    except IndexError:
        raise DBError(u'Такого автора не существует')
    return file

def get_need_update(file):
    if file.needupdate:
        return True

def get_genres_list():
    return _db.select('genres')

## ----------------------------------------------------------------------
## ф-ции для редактирования книги
## ----------------------------------------------------------------------

def edit_book_set_title(bookid, title):
    try:
        old = _db.select('books', locals(), where='id = $bookid')[0].title
    except IndexError:
        return
    _db.update('books', where='id = $bookid', title=title, vars=locals())
    db_log(u'изменено название книги', oldvalue=old, bookid=bookid,
           needupdate=True)

def edit_book_set_form(bookid, form):
    try:
        old = _db.select('books', locals(), where='id = $bookid')[0].form
    except IndexError:
        return
    _db.update('books', where='id = $bookid', form=form, vars=locals())
    db_log(u'изменена форма книги', oldvalue=old, bookid=bookid)
    #needupdate=True)

def edit_book_set_year(bookid, year):
    try:
        old = _db.select('books', locals(), where='id = $bookid')[0].year
    except IndexError:
        return
    _db.update('books', where='id=$bookid', year=year, vars=locals())
    if old:
        db_log(u'изменён год написания книги', oldvalue=old, bookid=bookid,
               needupdate=True)
    else:
        db_log(u'установлен год написания книги', bookid=bookid, needupdate=True)

def edit_book_set_lang(bookid, lang):
    try:
        old = _db.select('books', locals(), where='id = $bookid')[0].lang
    except IndexError:
        return
    _db.update('books', where='id = $bookid', lang=lang, vars=locals())
    if old:
        db_log(u'изменён язык книги', oldvalue=old, bookid=bookid,
               needupdate=True)
    else:
        db_log(u'установлен язык книги', bookid=bookid, needupdate=True)

def edit_book_add_alttitle(bookid, title):
    try:
        _db.select('alttitles', locals(),
                   where='title = $title and bookid = $bookid')[0]
    except IndexError:
        pass
    else:
        raise DBError(u'Такое название у этой книги уже есть.')
    _db.insert('alttitles', False, bookid=bookid, title=title)
    db_log(u'в книгу добавлено альтернативное название', bookid=bookid, needupdate=True)

def edit_book_del_alttitle(bookid, titleid):
    try:
        old = _db.select('alttitles', locals(),
                         where='id = $titleid and bookid = $bookid')[0].title
    except IndexError:
        raise DBError(u'Такого названия у этой книги нет.')
    _db.delete('alttitles', vars=locals(),
               where='id = $titleid and bookid = $bookid')
    db_log(u'из книги удалено альтернативное название', oldvalue=old, bookid=bookid, needupdate=True)

def edit_book_add_genre(bookid, genreid):
    res = list(_db.select('genres', locals(), where='id = $genreid'))
    if not res:
        raise DBError(u'Жанр не найден')
    try:
        res = _db.select('booksgenres', locals(),
                         where='genreid = $genreid and bookid = $bookid')[0]
    except IndexError:
        pass
    else:
        raise DBError(u'Такой жанр у этой книги уже есть')
    _db.insert('booksgenres', False, genreid=genreid, bookid=bookid)
    db_log(u'в книгу добавлен жанр', genreid=genreid, bookid=bookid,
           needupdate=True)

def edit_book_del_genre(bookid, genreid):
    try:
        res = _db.select('booksgenres', locals(),
                         where='genreid = $genreid and bookid = $bookid')[0]
    except IndexError:
        raise DBError(u'Такого жанра у этой книги нет')
    oldvalue = res.genreid
    try:
        res = _db.select('booksgenres', locals(), where='bookid = $bookid')[1]
    except IndexError:
        raise DBError(u'Это последний жанр у этой книги. Сначала добавьте новый жанр.')
    _db.delete('booksgenres', vars=locals(),
               where='genreid = $genreid and bookid = $bookid')
    db_log(u'из книги удалён жанр', bookid=bookid, genreid=genreid,
           oldvalue=oldvalue, needupdate=True)

def edit_book_search_author(bookid, author):
    '''поиск подходящего автора для добавления'''
    try:
        # попробуем считать это authorid
        authorid = int(author)
    except ValueError:
        # попробуем считать это фамилией
        res = list(_db.select('authors', locals(),
                              where='lower(lastname) = lower($author)'))
    else:
        # если это authorid, проверяем наличие
        res = list(_db.select('authors', locals(), where='id = $authorid'))
    return res

def edit_book_add_author(bookid, authorid):
    '''добавляем автора в книгу'''
    try:
        _db.select('books', locals(), where='id=$bookid')[0]
    except IndexError:
        raise DBError(u'Такая книга не найдена.')
    try:
        _db.select('authors', locals(), where='id = $authorid')[0]
    except IndexError:
        raise DBError(u'Такой автор не найден.')
    try:
        _db.select('booksauthors', locals(),
                   where='bookid = $bookid and authorid = $authorid')[0]
    except IndexError:
        pass
    else:
        raise DBError(u'Такой автор у этой книги уже есть.')
    _db.insert('booksauthors', False, bookid=bookid, authorid=authorid)
    db_log(u'в книгу добавлен автор', bookid=bookid, authorid=authorid,
           needupdate=True)
    return True

def edit_book_del_author(bookid, authorid):
    try:
        _db.select('booksauthors', locals(),
                   where='authorid = $authorid and bookid = $bookid')[0]
    except IndexError:
        raise DBError(u'Такого автора у этой книги нет')
    try:
        _db.select('authors', locals(), where='id = $authorid')[0]
    except IndexError:
        raise DBError(u'Такого автора не существует')
    try:
        _db.select('booksauthors', locals(), where='bookid = $bookid')[1]
    except IndexError:
        raise DBError(u'Это последний автор у этой книги. Сначала добавьте нового.')
    _db.delete('booksauthors', vars=locals(),
               where='authorid = $authorid and bookid = $bookid')
    db_log(u'из книги удалён автор', bookid=bookid, authorid=authorid,
           oldvalue=authorid, needupdate=True)

def edit_book_add_translator(bookid, authorid):
    '''добавляем переводчика в книгу'''
    try:
        _db.select('books', locals(), where='id = $bookid')[0]
    except IndexError:
        raise DBError(u'Такая книга не найдена.')
    try:
        _db.select('authors', locals(), where='id = $authorid')[0]
    except IndexError:
        raise DBError(u'Такой автор не найден.')
    try:
        _db.select('bookstranslators', locals(),
                   where='bookid = $bookid and authorid = $authorid')[0]
    except IndexError:
        pass
    else:
        raise DBError(u'Такой переводчик у этой книги уже есть.')
    _db.insert('bookstranslators', False, bookid=bookid, authorid=authorid)
    db_log(u'в книгу добавлен переводчик', bookid=bookid, authorid=authorid,
           needupdate=True)
    return True

def edit_book_del_translator(bookid, authorid):
    try:
        _db.select('bookstranslators', locals(),
                   where='authorid = $authorid and bookid = $bookid')[0]
    except IndexError:
        raise DBError(u'Такого переводчика у этой книги нет')
    try:
        _db.select('authors', locals(), where='id = $authorid')[0]
    except IndexError:
        raise DBError(u'Такого автора не существует')
    _db.delete('bookstranslators', vars=locals(),
               where='authorid = $authorid and bookid = $bookid')
    db_log(u'из книги удалён переводчик', bookid=bookid, authorid=authorid,
           oldvalue=authorid, needupdate=True)

def edit_book_search_file(bookid, file):
    '''поиск подходящего файла для добавления'''
    try:
        # id ?
        fileid = int(file)
    except ValueError:
        # title ?
        res = list(_db.select('files', locals(),
                              where='lower(title) = lower($file)'))
    else:
        # проверяем наличие
        res = list(_db.select('files', locals(), where='id = $fileid'))
    return res

def edit_book_add_file(bookid, fileid):
    '''добавляем файла в книгу'''
    try:
        _db.select('books', locals(), where='id = $bookid')[0]
    except IndexError:
        raise DBError(u'Такая книга не найдена.')
    try:
        _db.select('files', locals(), where='id = $fileid')[0]
    except IndexError:
        raise DBError(u'Такой файл не найден.')
    try:
        _db.select('booksfiles', locals(),
                   where='bookid = $bookid and fileid = $fileid')[0]
    except IndexError:
        pass
    else:
        raise DBError(u'Такой файл у этой книги уже есть.')
    _db.insert('booksfiles', False, bookid=bookid, fileid=fileid)
    db_log(u'в книгу добавлен файл', bookid=bookid, fileid=fileid)
    return True

def edit_book_del_file(bookid, fileid):
    try:
        _db.select('booksfiles', locals(),
                   where='fileid = $fileid and bookid = $bookid')[0]
    except IndexError:
        raise DBError(u'Такого файла у этой книги нет')
    try:
        _db.select('booksfiles', locals(), where='fileid = $fileid')[1]
    except IndexError:
        raise DBError(u'Это последняя книга у этого файла. Сначала добавьте этот файл в другую книгу.')
    _db.delete('booksfiles', vars=locals(),
               where='fileid = $fileid and bookid = $bookid')
    db_log(u'из книги удалён файл', bookid=bookid, fileid=fileid, oldvalue=fileid)

def edit_book_hide_file(bookid, fileid, action=None):
    '''спрятать/показать файл
    если action == None - меняем режим на противоположный'''
    try:
        res = _db.select('booksfiles', locals(), what='hidden',
                            where='fileid = $fileid and bookid = $bookid')[0]
    except IndexError:
        raise DBError(u'Такого файла у этой книги нет')
    hidden = res.hidden
    if action is not None:
        if action == 'hide' and hidden:
            # уже
            return
        if action == 'show' and not hidden:
            return
    if hidden:
        # показываем
        _db.update('booksfiles', where='fileid = $fileid and bookid = $bookid',
                   hidden='false', vars=locals())
        db_log(u'в книге открыт файл', bookid=bookid, fileid=fileid)
    else:
        # прячем
        try:
            _db.select('booksfiles', locals(),
                       where='bookid=$bookid and hidden=false')[1]
        except IndexError:
            raise DBError(u'Это последний видимый файл у этой книги. Сначала сделайте видимым другой файл.')
        _db.update('booksfiles', where='fileid = $fileid and bookid = $bookid',
                   hidden='true', vars=locals())
        db_log(u'в книге спрятан файл', bookid=bookid, fileid=fileid)

def edit_book_del_book(bookid):
    '''пометить книгу как удалённую'''
    try:
        _db.select('booksfiles', locals(), where='bookid = $bookid')[0]
    except:
        pass
    else:
        raise DBError(u'У книги имеются файлы. Сначала переместите их в другую книгу')
    db_log(u'книга удалена', bookid=bookid)
    _db.update('books', where='id = $bookid', deleted=True, vars=locals())

def edit_book_search_book(book):
    '''поиск подходящей книги для объединения'''
    try:
        # id ?
        bookid = int(book)
    except ValueError:
        # title ?
        res = list(_db.select('books', locals(),
                              where='lower(title) = lower($book)'))
    else:
        # проверяем наличие книги с таким id
        res = list(_db.select('books', locals(), where='id = $bookid'))
    return res

def edit_book_join_books(bookid, otherbookid, jointitles=True):
    '''объединение книг (bookid -> otherbookid)
    1. перенести все файлы из одной книги в другую
    2. удалить книгу (пометить как удалённую)
    3. (optional) объединить названия'''
    try:
        _db.select('books', locals(), where='id=$otherbookid')[0]
        # сохраняем title для последующего добавления в др. названия
        title = _db.select('books', locals(), where='id = $bookid')[0].title
    except IndexError:
        raise DBError(u'Такая книга не найдена.')
    res = list(_db.select('booksfiles', locals(), where='bookid = $bookid'))
    if res:
        # у книги есть файлы - переносим
        for f in res:
            _db.insert('booksfiles', False, bookid=otherbookid, fileid=f.fileid)
            db_log(u'файл удалён из книги', bookid=bookid, fileid=f.fileid)
            db_log(u'файл добавлен в книгу', bookid=otherbookid, fileid=f.fileid)
        _db.delete('booksfiles', vars=locals(), where='bookid = $bookid')
    # помечаем как удалённую
    _db.update('books', where='id = $bookid', deleted=True, vars=locals())
    if jointitles:
        # объединяем названия
        try:
            edit_book_add_alttitle(otherbookid, title)
        except DBError:
            pass
        res = _db.select('alttitles', locals(), where='bookid = $bookid')
        for b in res:
            try:
                edit_book_add_alttitle(otherbookid, b.title)
            except DBError:
                pass
    db_log(u'книга удалена при объединении', bookid=bookid)
    return True

def edit_book_add_sequence(bookid, sequenceid, sequencenumber):
    '''добавляет сериал в книгу'''
    res = add_sequence(bookid, sequenceid, sequencenumber)
    if not res:
        raise DBError(u'Сериал уже добавлен.')

def edit_book_del_sequence(bookid, sequenceid):
    try:
        res = _db.select('bookssequences', locals(),
                         where='sequenceid = $sequenceid and bookid = $bookid')[0]
    except IndexError:
        raise DBError(u'Такого сериала у этой книги нет')
    oldvalue = res.sequencenumber
    _db.delete('bookssequences', vars=locals(),
               where='sequenceid = $sequenceid and bookid = $bookid')
    db_log(u'из книги удалён сериал', bookid=bookid, sequenceid=sequenceid,
           oldvalue=oldvalue, needupdate=True)
##     # удаляем из sequences если сериал больше ни одной книгой не используется
##     try:
##         _db.query('select * from bookssequences, sequences '
##                   'where bookssequences.sequenceid = sequences.id '
##                   'and sequences.id = $sequenceid', vars=locals())[0]
##     except IndexError:
##         # и если он не является родительским
##         try:
##             _db.select('sequences', where='sequences.parrent=$sequenceid',
##                        vars=locals())[0]
##         except IndexError:
##             _db.delete('sequences', vars=locals(), where='id = $sequenceid')
##             db_log(u'удалён сериал', sequenceid=sequenceid)

def edit_book_add_publ_sequence(bookid, sequenceid, sequencenumber):
    '''добавляет издательскую серию в книгу'''
    res = add_sequence(bookid, sequenceid, sequencenumber)
    if not res:
        raise DBError(u'Серия уже добавлен.')

def edit_book_del_publ_sequence(bookid, sequenceid):
    try:
        res = _db.select('bookspublsequences', locals(),
                         where='sequenceid = $sequenceid and bookid = $bookid')[0]
    except IndexError:
        raise DBError(u'Такого издательской серии у этой книги нет')
    oldvalue = res.sequencenumber
    _db.delete('bookspublsequences', vars=locals(),
               where='sequenceid = $sequenceid and bookid = $bookid')
    db_log(u'из книги удалена издательская серия', bookid=bookid,
           publsequenceid=sequenceid, oldvalue=oldvalue, needupdate=True)
##     # удаляем из publsequences если сериал больше ни одной книгой не используется
##     res = _db.query('select * from bookssequences, publsequences '
##                     'where bookssequences.sequenceid = publsequences.id '
##                     'and publsequences.id = $sequenceid', vars=locals())
##     try:
##         res[0]
##     except IndexError:
##         _db.delete('publsequences', vars=locals(), where='id = $sequenceid')
##         db_log(u'удалена издательская серия', publsequenceid=sequenceid)

def edit_book_set_publ_year(bookid, year):
    try:
        old = _db.select('books', locals(), where='id = $bookid')[0].publyear
    except IndexError:
        return
    _db.update('books', where='id = $bookid', publyear=year, vars=locals())
    if old:
        db_log(u'изменён год издания', oldvalue=old, bookid=bookid,
               needupdate=True)
    else:
        db_log(u'установлен год издания', bookid=bookid, needupdate=True)

def edit_book_set_publ_lang(bookid, lang):
    try:
        old = _db.select('books', locals(), where='id = $bookid')[0].publlang
    except IndexError:
        return
    _db.update('books', where='id = $bookid', publlang=lang, vars=locals())
    if old:
        db_log(u'изменён язык издания', oldvalue=old, bookid=bookid,
               needupdate=True)
    else:
        db_log(u'установлен язык издания', bookid=bookid, needupdate=True)

## ----------------------------------------------------------------------

def edit_author_set_name(authorid, **kwargs):
    '''изменение имени автора
    kwargs - ключ: first/middle/last/nickname; значение: новое значение'''
    n = kwargs.keys()[0]
    assert n in ('firstname', 'middlename', 'lastname', 'nickname')
    res = _db.select('authors', locals(), where='id = $authorid')[0]
    oldvalue = res[n]
    _db.update('authors', where='id=$authorid', vars=locals(), **kwargs)
    if n == 'firstname':
        db_log(u'у автора изменено имя', authorid=authorid,
               oldvalue=oldvalue, needupdate=True)
    elif n == 'middlename':
        db_log(u'у автора изменено отчество', authorid=authorid,
               oldvalue=oldvalue, needupdate=True)
    elif n == 'lastname':
        db_log(u'у автора изменена фамилия', authorid=authorid,
               oldvalue=oldvalue, needupdate=True)
    elif n == 'nickname':
        db_log(u'у автора изменён псевдоним', authorid=authorid,
               oldvalue=oldvalue, needupdate=True)

def edit_author_set_biography(authorid, txt):
    try:
        res = _db.select('authorsdesc', locals(), where='authorid = $authorid')[0]
    except IndexError:
        _db.insert('authorsdesc', False, authorid=authorid, body=txt)
        db_log(u'добавлена биография автора', authorid=authorid)
    else:
        oldvalue = res.body
        _db.update('authorsdesc', vars=locals(), where='authorid = $authorid',
                   body=txt)
        db_log(u'изменена биография автора', authorid=authorid, oldvalue=oldvalue)

def edit_author_add_alias(authorid, name=None, **alias):
    if name is not None:
        # for undo
        for n in ('firstname', 'middlename', 'lastname', 'nickname'):
            alias[n] = name[n]
    where = ' and '.join('%s=$%s' % (n, n) for n in alias)
    alias['authorid'] = authorid
    try:
        res = _db.select('authorsaliases', alias,
                         where=where+' and authorid = $authorid')[0]
    except IndexError:
        pass
    else:
        raise DBError(u'Такой алиас у этого автора уже есть')
    try:
        res = _db.select('authorsaliases', alias, where=where)[0]
    except IndexError:
        pass
    else:
        raise DBError(u'Такой алиас уже есть: id=%s' % res.authorid)
    _db.insert('authorsaliases', False, **alias)
    db_log(u'автору добавлен алиас', authorid=authorid)

def edit_author_del_alias(authorid, aliasid):
    a = _db.select('authorsaliases', locals(), where='id = $aliasid')[0]
    strvalue = 'firstname=(%s) middlename=(%s) lastname=(%s) nickname=(%s)' \
               % (a.firstname, a.middlename, a.lastname, a.nickname)
    _db.delete('authorsaliases', vars=locals(), where='id = $aliasid')
    db_log(u'у автора удалён алиас', authorid=authorid, oldvalue=a,
           strvalue=strvalue)

## ----------------------------------------------------------------------

def edit_sequence_set_name(sequenceid, name):
    try:
        old = _db.select('sequences', locals(), where='id = $sequenceid')[0].name
    except IndexError:
        raise DBError(u'Неправильный сериал')
    _db.update('sequences', where='id = $sequenceid', name=name, vars=locals())
    db_log(u'изменено название сериала', oldvalue=old, sequenceid=sequenceid,
           needupdate=True)
    return True

def edit_sequence_set_parrent(sequenceid, parsequenceid, sequencenumber):
    try:
        _db.select('sequences', locals(), where='id = $sequenceid')[0]
    except IndexError:
        raise DBError(u'Неправильный сериал')
    try:
        _db.select('sequences', locals(), where='id = $parsequenceid')[0]
    except IndexError:
        raise DBError(u'Неправильный родительский сериал')
    sequenceid = int(sequenceid)
    if sequenceid == parsequenceid:
        raise DBError(u'Нельзя присвоить родительский сериал самому себе')
    if not sequencenumber:
        sequencenumber = 0
    try:
        sequencenumber = int(sequencenumber)
    except ValueError:
        raise DBError(u'Неправильный порядковый номер в сериале')
    _db.update('sequences', where='id = $sequenceid', vars=locals(),
               parrent=parsequenceid, number=sequencenumber)
    db_log(u'добавлен родительский сериал', sequenceid=sequenceid)
    return True

def edit_sequence_del_parrent(sequenceid):
    try:
        _db.select('sequences', locals(), where='id = $sequenceid')[0]
    except IndexError:
        raise DBError(u'Неправильный сериал')
    _db.update('sequences', where='id = $sequenceid', vars=locals(), parrent=None)
    db_log(u'удалён родительский сериал', sequenceid=sequenceid)
    return True

def edit_sequence_set_number(sequenceid, bookid, sequencenumber):
    try:
        sequencenumber = int(sequencenumber)
    except ValueError:
        raise DBError(u'Неправильный порядковый номер в сериале')
    try:
        old = _db.select('bookssequences', locals(),
                         where='bookid = $bookid and sequenceid = $sequenceid'
                         )[0].sequencenumber
    except IndexError:
        raise DBError(u'Неправильный сериал')
    _db.update('bookssequences',
               where='bookid = $bookid and sequenceid = $sequenceid',
               sequencenumber=sequencenumber, vars=locals())
    db_log(u'у книги изменён порядковый номер в сериале', oldvalue=str(old),
           bookid=bookid, sequenceid=sequenceid, needupdate=True)
    return True

## ----------------------------------------------------------------------

def edit_file_set_title(fileid, title):
    try:
        old = _db.select('files', locals(), where='id = $fileid')[0].title
    except IndexError:
        return
    _db.update('files', where='id = $fileid', title=title, vars=locals())
    db_log(u'изменён заголовок файла', oldvalue=old, fileid=fileid,
           needupdate=True)

def file_update_filename(fileid, fn):
    _db.update('files', where='id = $fileid', filename=fn, vars=locals())

def file_get_images(fileid, what='images'):
    res = _db.select('files', locals(), where='id = $fileid',
                     what=what)[0]
    images = pickle.loads(safestr(res[what]))
    return images

## ----------------------------------------------------------------------

def book_search(query):
    n = 0                               # кол-во найденного
    tsquery = "@@plainto_tsquery('russian', $query)"
    # 1. авторы
    where="to_tsvector('russian', firstname||' '||middlename||' '||lastname||' '||nickname)"+tsquery
    authors = list(_db.select('authors', locals(), where=where,
                              order='lastname, firstname, middlename'))
    n = len(authors)
    # 2. псевдонимы авторов
    aliases = list(_db.select('authorsaliases', locals(), where=where,
                              order='lastname, firstname, middlename'))
    # 3. название книги
    books = list(_db.select('books', locals(),
                            where="to_tsvector('russian', title)"+tsquery,
                            order='title'))
    for b in books:
        add_authors_to_book(b, limit=1)
    n += len(books)
    # 4. альтернативные названия
    alttitles = list(_db.query(
        'select books.*, alttitles.title as alttitle '
        'from books, alttitles where books.id = alttitles.bookid '
        "and to_tsvector('russian', alttitles.title)"+tsquery, vars=locals()))
    for b in alttitles:
        add_authors_to_book(b, limit=1)
    n += len(alttitles)
    # 5. авторские сериалы
    sequences = list(_db.select('sequences', locals(),
                                where="to_tsvector('russian', name)"+tsquery,
                                order='name'))
    n += len(sequences)
    # издательские серии
    # файлы (заголовки)
    return n, authors, aliases, books, alttitles, sequences

## ----------------------------------------------------------------------

def get_recent_changes(page=None, limit=100, watchlist=[], **kwargs):
    where = ''
    if kwargs:
        where = ' and '.join('%s=$%s' % (i,i) for i in kwargs)
    if watchlist:
        # watchlist - возвращается функцией get_watched_items
        where += ' or '.join('%sid=%s' % (i.what, i.itemid) for i in watchlist)
    if where:
        where = ' where ' + where
    numpages, count, changes = _paging_select(
        'select *', 'from actions'+where, 'order by ctime desc',
        page, limit, kwargs)
    for c in changes:
        pages = []
        for p in c.pages.splitlines():
            pages.append(p.split(' ', 3))
        c.pages = pages
        if c.valuechanged:
            oldvalue = _db.select('oldvalues', locals(),
                                  where='actionid = $c.id')[0]
            if oldvalue.dumped:
                oldvalue = oldvalue.str
            else:
                oldvalue = oldvalue.body
        else:
            oldvalue = None
        c.oldvalue = oldvalue
    return changes, numpages

def get_oldvalue(actionid):
    try:
        res = _db.select('oldvalues', locals(),
                         where='actionid = $actionid')[0]
    except IndexError:
        raise DBError(u'неправильное значение actionid')
    if res.dumped:
        oldvalue = res.str
    else:
        oldvalue = res.body
    return oldvalue

def get_statistics():
    authors = _db.select('authors', what='count(*)', where='not deleted')[0].count
    books = _db.select('books', what='count(*)', where='not deleted')[0].count
    # TODO: исключить спрятанные файлы
    files = _db.select('files', what='count(*)')[0].count
    return web.Storage(authors=authors, books=books, files=files)

def get_new_books(page=None, limit=100, filter=None):
    numpages, count, newbooks = _paging_select(
        'select books.*',
        "from books, actions where actions.bookid = books.id "
        "and actions.action = 'в библиотеку добавлена книга' and "
        "not books.deleted", 'order by books.created desc',
        page, limit)
    for b in newbooks:
        add_genres_to_book(b)
        add_authors_to_book(b, limit=1)
        add_files_to_book(b)
    return newbooks, numpages

def get_new_files(page=None, limit=100):
    numpages, count, newfiles = _paging_select(
        'select files.*',
        "from files, actions, booksfiles "
        "where actions.fileid = files.id "
        "and files.id = booksfiles.fileid "
        "and actions.action = 'в библиотеку добавлен файл' "
        "and not booksfiles.hidden",
        'order by files.added desc',
        page, limit)
    return newfiles, numpages

def add_watch(username, what, itemid):
    if is_watched(username, what, itemid):
        _db.delete('watchlist', vars=locals(),
                   where='username=$username and what=$what and itemid=$itemid')
        return False
    _db.insert('watchlist', False, username=username, what=what, itemid=itemid)
    return True

def is_watched(username, what, itemid):
    if not username:
        return False
    try:
        _db.select('watchlist', locals(),
                   where=('username = $username and '
                          'what = $what and itemid = $itemid'))[0]
    except IndexError:
        return False
    return True

def get_watched_items(username):
    '''возвращает list с наблюдаемыми items'''
    watchlist = list(_db.select('watchlist', locals(),
                                where='username = $username'))
    return watchlist

def get_watch_list(username):
    '''возвращает список наблюдения пользователя'''
    watchlist = list(_db.select('watchlist', locals(),
                                where='username = $username'))
    for item in watchlist:
        if item.what == 'book':
            book = get_book_info(item.itemid)
            item.what = u'Книга'
            item.url = '/book/'+str(book.id)
            item.title = book.title
            item.delurl = '/watch/book/'+str(book.id)
        elif item.what == 'author':
            author = get_author_info(item.itemid)
            item.what = u'Автор'
            item.url = '/author/'+str(author.id)
            item.title = authorname(author)
            item.delurl = '/watch/author/'+str(author.id)
        elif item.what == 'file':
            file = get_file_info(item.itemid)
            item.what = u'Файл'
            item.url = '/file/'+str(file.id)
            item.title = file.title
            item.delurl = '/watch/file/'+str(file.id)

    return watchlist

def update_download_stat(username, fileid, filetype):
    try:
        num = _db.select('downloads', locals(),
                         where='fileid = $fileid and filetype = $filetype')[0].num
    except IndexError:
        _db.insert('downloads', False, fileid=fileid, filetype=filetype, num=1)
    else:
        _db.update('downloads', vars=locals(), num=num+1,
                   where='fileid = $fileid and filetype = $filetype')

def save_fb2_errors(fileid, errors):
    if not errors:
        return
    numerrors = numwarnings = 0
    for e in errors:
        if e.startswith('WARNING'):
            numwarnings += 1
        else:
            numerrors += 1
    errors = '\n'.join(errors)
    _db.insert('fb2errors', False, fileid=fileid, numerrors=numerrors,
               numwarnings=numwarnings, errors=errors)

## ----------------------------------------------------------------------
## админское
## ----------------------------------------------------------------------

def block_user(username, reason='', who='', what='', action='isblocked'):
    if action == 'isblocked':
        # проверяем наличие блокировки
        blocked = web.Storage(isblocked=False, reason='')
        try:
            res = _db.select('blockedusers', locals(),
                             where='username = $username')[0]
        except IndexError:
            return blocked
        blocked.isblocked = True
        blocked.reason = res.reason
        return blocked
    elif action == 'block':
        # блокируем пользователя
        _db.insert('blockedusers', False, username=username,
                   reason=reason, who=who, what=what)
    elif action == 'unblock':
        # разблокируем пользователя
        _db.delete('blockedusers', vars=locals(), where='username = $username')
    return True

def edit_book_block(bookid):
    try:
        book = _db.select('books', locals(), where='id = $bookid')[0]
    except IndexError:
        return None
    if book.permission == 0:
        _db.update('books', where='id = $bookid', permission=1, vars=locals())
        return 1
    _db.update('books', where='id = $bookid', permission=0, vars=locals())
    db_log(u'книга заблокирована', bookid=bookid)
    return 0

## ----------------------------------------------------------------------
## оценки, отзывы
## ----------------------------------------------------------------------

def add_books_to_reviews(reviews):
    for r in reviews:
        book = _db.select('books', locals(), where='id = $r.bookid')[0]
        add_authors_to_book(book, limit=1)
        add_genres_to_book(book)
        r.book = book

def _get_reviews(vars, where, page=None, limit=100):
##     numpages, count, reviews = _paging_select(
##         'select *', 'from reviews where '+where, 'order by mtime',
##         page, limit, vars)
    reviews = list(_db.select('reviews', vars, where=where, order='mtime'))
    return reviews

def get_all_reviews(page=None, limit=100):
    numpages, count, reviews = _paging_select(
        'select *', 'from reviews where bookid is not null',
        'order by mtime desc', page, limit)
    add_books_to_reviews(reviews)
    return reviews, numpages, count

def get_user_reviews(username=None, item='book', page=None, limit=100):
    if username:
        where = 'username = $username and '
    else:
        where = ''
    if item == 'book':
        # отзывы к книгам
        reviews = _get_reviews(locals(), where+'bookid is not null')
        add_books_to_reviews(reviews)
    elif item == 'file':
        # отзывы к файлам
        reviews = _get_reviews(locals(), where+'fileid is not null')
    else:
        # автор
        reviews = _get_reviews(locals(), where+'authorid is not null')
    return reviews

def _update_booksratings(bookid, rating, oldrating=None):
    where='bookid = $bookid'
    try:
        res = _db.select('booksratings', locals(), where='bookid = $bookid')[0]
    except IndexError:
        # первая оценка для этой книги
        _db.insert('booksratings', False, bookid=bookid, sum=rating, num=1)
    else:
        if oldrating:
            # пользователь изменил свою оценку
            r = rating - oldrating
            sum = res.sum + r
            if rating:
                num = res.num
            else:
                # пользователь удалил свою оценку
                num = res.num - 1
        else:
            # первая оценка пользователем этой книги
            sum = res.sum + rating
            num = res.num + 1
        _db.update('booksratings', vars=locals(), where=where, sum=sum, num=num)

def _update_matrix(action, username, bookid, rating, oldrating=0):
    bookid1 = bookid
    try:
        rating1 = int(rating)
    except:
        rating1 = 0
    res = _db.select('ratings', locals(), where='username = $username')
    for r in res:
        # проходим по всем оценкам пользователя
        bookid2 = r.bookid
        rating2 = r.rating
        if action == 'insert':
            diff = rating1 - rating2
            n = 1
        elif action == 'update':
            diff = rating1 - oldrating
            n = 0
        else:
            # delete
            diff = -oldrating
            n = -1
        if bookid1 == bookid2:
            continue
        elif bookid1 > bookid2:
            b1, b2 = bookid1, bookid2
        else:
            # bookid1 < bookid2
            b1, b2 = bookid2, bookid1
            diff = -diff
        where='bookid1 = $b1 and bookid2 = $b2'
        try:
            m = _db.select('matrix', locals(), where=where)[0]
        except IndexError:
            _db.insert('matrix', False, bookid1=b1, bookid2=b2,
                       num=n, sum=diff)
        else:
            n = m.num+n
            if n == 0:
                _db.delete('matrix', vars=locals(), where=where)
            else:
                _db.update('matrix', vars=locals(), where=where,
                           num=n, sum=m.sum+diff)

def book_set_rating(username, bookid, rating):
    where='bookid = $bookid and username = $username'
    try:
        res = _db.select('ratings', locals(), where=where)[0]
    except IndexError:
        # пользователь ещё не оценивал эту книгу
        if not rating:
            return
        _update_matrix('insert', username, bookid, rating)
        if not rating:
            return
        _db.insert('ratings', False, username=username,
                   bookid=bookid, rating=rating)
        # добавляем в booksratings
        _update_booksratings(bookid, rating)
    else:
        # пользователь уже оценивал эту книгу и сейчас поменял оценку
        oldrating = res.rating          # старая оценка пользователя
        if rating:
            _update_matrix('update', username, bookid, rating, oldrating)
            _db.update('ratings', vars=locals(), where=where, rating=rating)
            # обновляем booksratings
            _update_booksratings(bookid, rating, oldrating)
        else:
            # пользователь удалил свою оценку
            _update_matrix('delete', username, bookid, rating)
            _db.delete('ratings', vars=locals(), where=where)
            _update_booksratings(bookid, 0, oldrating)

def book_get_user_opinion(username, bookid):
    '''возвращает
    оценки книги (totalsum, totalnum)
    оценку пользователя этой книге (rating)
    и список отзывов к этой книге (reviews)'''
    try:
        res = _db.select('booksratings', locals(), where='bookid = $bookid')[0]
    except IndexError:
        totalsum = 0
        totalnum = 0
    else:
        totalsum = res.sum
        totalnum = res.num
    rating = ''
    if username:
        try:
            rating = _db.select('ratings', locals(),
                                where=('username = $username and '
                                       'bookid = $bookid'))[0]
            rating = rating.rating
        except IndexError:
            pass
    reviews = _get_reviews(locals(), 'bookid = $bookid')
    return (totalsum, totalnum, rating, reviews)

def get_suggest(username):
    mybooks = set()
    mymatrix = {}
    res = _db.select('ratings', locals(), where='username = $username')
    for r in res:
        bookid = r.bookid
        rating = r.rating
        mybooks.add(bookid)
        mat = _db.select('matrix', locals(),
                         where='bookid1 = $bookid or bookid2 = $bookid')
        for m in mat:
            if m.bookid1 == bookid:
                diffitem = m.bookid2
            else:
                diffitem = m.bookid1
            freq = m.num
            diffrating = float(m.sum)/m.num
            mymatrix.setdefault(diffitem, [0, 0.0])
            mymatrix[diffitem][0] += freq
            mymatrix[diffitem][1] += freq * (diffrating + rating)
    #
    suggest = []
    for bookid in mymatrix:
        if bookid in mybooks:
            continue
        if mymatrix[bookid][0] == 0:
            continue
        book = get_book_info(bookid)
        add_authors_to_book(book)
        book.rating = round(rating, 2)
        rating = mymatrix[bookid][1] / mymatrix[bookid][0]
        suggest.append((rating, book))
    suggest.sort()
    suggest.reverse()
    return suggest

def get_same_books(bookid, limit=10):
    bookid = int(bookid)
    minrating = 4.0                     # минимальное кол-во оценок
    avgrating = 10.0                    # средняя оценка всех книг
    # true Bayesian estimate
    bayes = ('(num / (num+$minrating)) * (10-abs(sum)/num)'
             ' + ($minrating / (num+$minrating)) * $avgrating')
    res = _db.select('matrix', locals(),
                     what='*, '+bayes+' as r',
                     where='bookid1 = $bookid or bookid2 = $bookid',
                     order='r desc', limit=limit)
    books = []
    for r in res:
        if r.bookid1 == bookid:
            b = r.bookid2
        else:
            b = r.bookid1
        book = get_book_info(b)
        #book.rating = round(r.r, 3)
        #book.num = r.num
        #book.diff = round(float(r.sum)/r.num, 3)
        add_authors_to_book(book)
        books.append(book)
    return books

def get_books_rating():
    minrating = 1.0                     # минимальное кол-во оценок
    avgrating = 7.0                     # средняя оценка всех книг
    avgrating = _db.select('booksratings', what='avg(sum/num)')[0].avg
    # используем true Bayesian estimate
    bayes = ('(num / (num+$minrating)) * (sum/num)'
             ' + ($minrating / (num+$minrating)) * $avgrating')
    res = _db.select('booksratings', locals(),
                     what='*, '+bayes+' as r', order='r desc')
    books = []
    for r in res:
        b = get_book_info(r.bookid)
        add_authors_to_book(b)
        b.rating = round(r.r, 3)
        books.append(b)
    return books

def file_get_user_opinion(username, fileid):
    reviews = _get_reviews(locals(), 'fileid = $fileid')
    return reviews

def author_get_user_opinion(username, authorid):
    reviews = _get_reviews(locals(), 'authorid = $authorid')
    return reviews

def get_review(reviewid):
    return _db.select('reviews', locals(), where='id = $reviewid')[0]

def add_review(**kwargs):
    _db.insert('reviews', False, **kwargs)

def change_review(reviewid, body, html):
    _db.query('update reviews set body = $body, html = $html, '
              'mtime=current_timestamp where id = $reviewid', vars=locals())

def delete_review(reviewid):
    _db.delete('reviews', vars=locals(), where='id = $reviewid')

def get_news(newsid=None):
    if newsid is None:
        return list(_db.select('news', order='ctime desc', limit=10))
    return _db.select('news', locals(), where='id = $newsid')[0]

def update_news(what='add', **kw):
    # kw: title, body, html, username, newsid
    if what == 'add':
        # kw: title, body, html, username
        _db.insert('news', False, **kw)
    elif what == 'edit':
        # kw: title, body, html, newsid
        _db.query('update news set title = $title, body = $body, '
                  'html = $html, mtime = current_timestamp '
                  'where id = $newsid', vars=kw)
    elif what == 'delete':
        # kw: newsid
        _db.delete('news', vars=kw, where='id = $newsid')

def get_user_prefs(username):
    if not username:
        return None
    try:
        return _db.select('usersprefs', locals(), where='username = $username')[0]
    except IndexError:
        return web.Storage(genres='', filetypes='', langs='')

def set_user_prefs(username, prefs):
    try:
        res = _db.select('usersprefs', locals(), where='username = $username')[0]
    except IndexError:
        prefs['username'] = username
        _db.insert('usersprefs', False, **prefs)
    else:
        _db.update('usersprefs', where='username = $username', **prefs)

## ----------------------------------------------------------------------

def test_suggest():
    suggest = get_suggest('admin')
    n = 0
    for rating, book in suggest:
        print '=>', round(rating, 3), book.id, book.title
        n += 1

if __name__ == '__main__':
    #get_recent_changes()
    #a = web.Storage(firstname='Урсула', middlename='', lastname='Ле Гуин')
    #print find_author(a)
    #book_set_rating(username, bookid, rating)
    #book_set_rating(sys.argv[1], int(sys.argv[2]), int(sys.argv[3]))
    #test_suggest()
    #get_books_rating()
    for b in get_same_books(45): print b.rating, b.num, b.diff, b.title
