#!/usr/bin/env python
# -*- mode: python; coding: utf-8; -*-
# (c) Lankier mailto:lankier@gmail.com
import web
import libdb
from utils import annotation2html, text2annotation, text2html
from validator import validate_annotation
from session import check_access

edit_urls = (
    #### страница редактирования книги
    '/editbook/(\\d+)', 'EditBookPage',
    '/editbook/(\\d+)/block', 'EditBookBlockPage',
    # изменение названия, года, языка
    '/editbook/(\\d+)/settitle', 'EditBookSetTitlePage',
    '/editbook/(\\d+)/setyear', 'EditBookSetYearPage',
    '/editbook/(\\d+)/setlang', 'EditBookSetLangPage',
    # добавление/удаление доп. названий
    '/editbook/(\\d+)/addalttitle', 'EditBookAddAltTitlePage',
    '/editbook/(\\d+)/delalttitle', 'EditBookDelAltTitlePage',
    # добавление/удаление авторов
    '/editbook/(\\d+)/addauthor', 'EditBookAddAuthorPage',
    '/editbook/(\\d+)/addauthor/(\\d+)', 'EditBookAddAuthorPage',
    '/editbook/(\\d+)/delauthor', 'EditBookDelAuthorPage',
    #'/editbook/(\\d+)/delauthor/(\\d+)', 'EditBookDelAuthorPage',
    # добавление/удаление жанров
    '/editbook/(\\d+)/addgenre', 'EditBookAddGenrePage',
    '/editbook/(\\d+)/addgenre/(.+)', 'EditBookAddGenrePage',
    '/editbook/(\\d+)/delgenre', 'EditBookDelGenrePage',
    #'/editbook/(\\d+)/delgenre/(.+)', 'EditBookDelGenrePage',
    # добавление/удаление авторских сериалов
    '/editbook/(\\d+)/addsequence', 'EditBookAddSequencePage',
    '/editbook/(\\d+)/delsequence', 'EditBookDelSequencePage',
    # манипуляции с файлами
    '/editbook/(\\d+)/addfile', 'EditBookAddFilePage',
    '/editbook/(\\d+)/addfile/(\\d+)', 'EditBookAddFilePage',
    '/editbook/(\\d+)/delfile', 'EditBookDelFilePage',
    # редактирование аннотации
    '/editbook/(\\d+)/editann', 'EditBookEditAnnPage',
    # объединение книг
    '/editbook/(\\d+)/join', 'EditBookJoinPage',
    '/editbook/(\\d+)/join/(\\d+)', 'EditBookJoinPage',
    #### страница редактирования авторского сериала
    '/editsequence/(\\d+)', 'EditSequencePage',
    '/editsequence/(\\d+)/setparrent', 'EditSequenceSetParrentPage',
    '/editsequence/(\\d+)/setparrent/(\\d+)', 'EditSequenceSetParrentPage',
    '/editsequence/(\\d+)/setnumber/(\\d+)', 'EditSequenceSetNumberPage',
    '/editsequence/(\\d+)/(.+)', 'EditSequencePage',
    #### страница редактирования файла
    '/editfile/(\\d+)', 'EditFilePage',
    '/editfile/(\\d+)/settitle', 'EditFileSetTitlePage',
    '/editfile/(\\d+)/setyear', 'EditFileSetYearPage',
    '/editfile/(\\d+)/addtranslator', 'EditFileAddTranslatorPage',
    '/editfile/(\\d+)/addtranslator/(\\d+)', 'EditFileAddTranslatorPage',
    '/editfile/(\\d+)/deltranslator', 'EditFileDelTranslatorPage',
    '/editfile/(\\d+)/addsequence', 'EditFileAddSequencePage',
    '/editfile/(\\d+)/delsequence', 'EditFileDelSequencePage',
    #### страница редактирования автора
    '/editauthor/(\\d+)', 'EditAuthorPage',
    '/editauthor/(\\d+)/setname', 'EditAuthorSetNamePage',
    '/editauthor/(\\d+)/biography', 'EditAuthorBiographyPage',
    '/editauthor/(\\d+)/addalias', 'EditAuthorAddAliasPage',
    '/editauthor/(\\d+)/delalias/(\\d+)', 'EditAuthorDelAliasPage',
    )

## ----------------------------------------------------------------------

def _add_sequence(itemid, sequenceid=None, publish=False, seeother='/editbook/'):
    i = web.input()
    newsequence = False     # устанавливается в True, если создан новый сериал
    if 'sequencename' in i:
        if not i.sequencename:
            err = u'Вы не ввели сериал'
            return render.add_sequence(itemid, seeother, err)
        # если такого сериала нет - будет создан
        try:
            sequenceid, newsequence = libdb.add_sequence(itemid, i.sequencename,
                                                         i.sequencenumber,
                                                         publish)
        except libdb.DBError, err:
            return render.add_sequence(itemid, seeother, err)
    if sequenceid:
        # успешно
        if newsequence:
            session.message = u'Создан новый сериал.'
        else:
            session.message = u'Сериал добавлен.'
        raise web.seeother(seeother+itemid)
    # форма выбора сериала
    return render.add_sequence(itemid, seeother)

def _set_title(itemid, title=None,
               seeother='/editbook/',
               set_title_func=libdb.edit_book_set_title,
               ):
    i = web.input()
    if 'title' in i:
        title = i.title
    if title:
        set_title_func(itemid, title)
        session.message = u'Название изменено'
    else:
        session.message = u'Ошибка. Пустое название'
    raise web.seeother(seeother+itemid)

def _set_year(itemid, year=None,
              seeother='/editbook/',
              set_year_func=libdb.edit_book_set_year,
              ):
    i = web.input()
    if 'year' in i:
        year = i.year
    if year:
        try:
            year = int(year)
        except ValueError:
            session.message = u'Ошибка. Неправильный год'
        else:
            set_year_func(itemid, year)
            session.message = u'Год изменён'
    raise web.seeother(seeother+itemid)

def _set_lang(itemid, lang=None,
              seeother='/editbook/',
              set_lang_func=libdb.edit_book_set_lang,
              ):
    i = web.input()
    if 'lang' in i:
        lang = i.lang
    if lang:
        set_lang_func(itemid, lang)
        session.message = u'Язык изменён'
    raise web.seeother(seeother+itemid)

def _add_author(itemid, authorid,
                seeother='/editbook/',
                addurl='/addauthor/',
                what=u'Автор',
                add_author_func=libdb.edit_book_add_author,
                search_author_func=libdb.edit_book_search_author,
                ):
    if  authorid is not None:
        # authorid указан в url
        try:
            add_author_func(itemid, authorid)
        except libdb.DBError, err:
            return render.edit_error(itemid, seeother, u'Ошибка', err)
        session.message = what+u' добавлен'
        raise web.seeother(seeother+itemid)
    i = web.input()
    if 'author' in i:
        # author указан в POST
        # ищем авторов
        authors = search_author_func(itemid, i.author)
        # отдаем страницу со списком найденных
        # authors может быть пустым списком, проверяется в шаблоне
        return render.add_author_found(itemid, seeother, addurl, authors)
    # форма поиска авторов
    s = what.lower()
    return render.add_smth(itemid, seeother, u'Добавить %sа'%s,
                           'author', u'Id или фамилия %sа:'%s)

def _del_author(itemid, authorid=None,
                seeother='/editbook/',
                what=u'Автор',
                del_author_func=libdb.edit_book_del_author,
                ):
    i = web.input()
    if 'authorid' in i:
        authorid = i.authorid
    if authorid:
        try:
            del_author_func(itemid, authorid)
        except libdb.DBError, err:
            return render.edit_error(itemid, seeother, u'Ошибка', err)
    session.message = what+u' удалён'
    raise web.seeother(seeother+itemid)

## ----------------------------------------------------------------------

class EditAuthorPage:
    def GET(self, authorid):
        check_access('edit_author', authorid)
        author = libdb.get_author(authorid, add_books=False)
        if not author:
            raise web.notfound()
        author.biography = text2html(author.biography)
        html = render.edit_author(author)
        session.message = ''            # сбрасываем сообщение
        return html

class EditAuthorSetNamePage:
    def GET(self, authorid):
        check_access('edit_author', authorid)
        i = web.input()
        if 'firstname' in i:
            libdb.edit_author_set_name(authorid, firstname=i.firstname)
            session.message = u'Имя изменено'
        elif 'middlename' in i:
            libdb.edit_author_set_name(authorid, middlename=i.middlename)
            session.message = u'Отчество изменено'
        elif 'lastname' in i:
            libdb.edit_author_set_name(authorid, lastname=i.lastname)
            session.message = u'Фамилия изменена'
        elif 'nickname' in i:
            libdb.edit_author_set_name(authorid, nickname=i.nickname)
            session.message = u'Псевдоним изменён'
        else:
            session.message = u'Ошибка. Неправильный запрос'
        raise web.seeother('/editauthor/'+authorid)
    POST = GET

class EditAuthorBiographyPage:
    def GET(self, authorid):
        check_access('edit_author', authorid)
        i = web.input()
        if 'biography' in i:
            libdb.edit_author_set_biography(authorid, i.biography)
            raise web.seeother('/editauthor/'+authorid)
        author = libdb.get_author(authorid, add_books=False)
        return render.edit_biography(author)
    POST = GET

class EditAuthorAddAliasPage:
    def POST(self, authorid):
        check_access('edit_author', authorid)
        i = web.input()
        if 'firstname' in i:
            try:
                libdb.edit_author_add_alias(authorid,
                                            firstname=i.firstname,
                                            middlename=i.middlename,
                                            lastname=i.lastname,
                                            nickname=i.nickname)
            except libdb.DBError, err:
                return render.add_alias(authorid, err)
            session.message = u'Алиас добавлен'
            web.seeother('/editauthor/'+authorid)
        return render.add_alias(authorid)

class EditAuthorDelAliasPage:
    def POST(self, authorid, aliasid):
        check_access('edit_author', authorid)
        try:
            libdb.edit_author_del_alias(authorid, aliasid)
        except:
            # FIXME
            session.message = u'Неправильный запрос'
        else:
            session.message = u'Алиас удалён'
        web.seeother('/editauthor/'+authorid)

## ----------------------------------------------------------------------
## редактирование книги
## ----------------------------------------------------------------------

class EditBookPage:
    def GET(self, bookid):
        check_access('edit_book', bookid)
        book = libdb.get_book(bookid, add_hidden_files=True)
        if not book:
            raise web.notfound()
        html = render.edit_book(book)
        session.message = ''            # сбрасываем сообщение
        return html

class EditBookBlockPage:
    def POST(self, bookid):
        check_access('admin')
        perm = libdb.edit_book_block(bookid)
        if perm == 0:
            session.message = u'Книга разблокирована'
        else:
            session.message = u'Книга заблокирована'
        raise web.seeother('/editbook/'+bookid)

class EditBookSetTitlePage:
    def GET(self, bookid, title=None):
        check_access('edit_book', bookid)
        return _set_title(bookid, title)
    POST = GET

class EditBookSetYearPage:
    def GET(self, bookid, year=None):
        check_access('edit_book', bookid)
        _set_year(bookid, year)
    POST = GET

class EditBookSetLangPage:
    def GET(self, bookid, lang=None):
        check_access('edit_book', bookid)
        _set_lang(bookid, lang)
    POST = GET

class EditBookAddAltTitlePage:
    def GET(self, bookid, title=None):
        check_access('edit_book', bookid)
        i = web.input()
        if 'title' in i:
            title = i.title
        if title:
            try:
                libdb.edit_book_add_alttitle(bookid, title)
            except libdb.DBError, err:
                return render.edit_book_error(bookid, u'Ошибка', err)
            session.message = u'Название добавлено'
            raise web.seeother('/editbook/'+bookid)
        return render.add_smth(bookid, '/edit_book/', u'Добавить другое название',
                               'title', u'Другое название книги:')
    POST = GET

class EditBookDelAltTitlePage:
    def GET(self, bookid, titleid=None):
        check_access('edit_book', bookid)
        i = web.input()
        if 'titleid' in i:
            titleid = i.titleid
        if titleid:
            try:
                libdb.edit_book_del_alttitle(bookid, titleid)
            except libdb.DBError, err:
                return render.edit_book_error(bookid, u'Ошибка', err)
        session.message = u'Название удалено'
        raise web.seeother('/editbook/'+bookid)
    POST = GET

class EditBookAddAuthorPage:
    def GET(self, bookid, authorid=None):
        check_access('edit_book', bookid)
        return _add_author(bookid, authorid)
    POST = GET

class EditBookDelAuthorPage:
    def GET(self, bookid, authorid=None):
        check_access('edit_book', bookid)
        return _del_author(bookid, authorid)
    POST = GET

class EditBookAddGenrePage:
    def GET(self, bookid, genreid=None):
        check_access('edit_book', bookid)
        i = web.input()
        if 'genre' in i:
            if not i.genre:
                err = u'Вы не ввели жанр'
                return render.add_genre(bookid, libdb.get_genres_list(), err)
            genreid = i.genre
        if genreid:
            # добавляем жанр
            try:
                libdb.edit_book_add_genre(bookid, genreid)
            except libdb.DBError, err:
                return render.add_genre(bookid, libdb.get_genres_list(), err)
            # успешно
            session.message = u'Жанр добавлен'
            raise web.seeother('/editbook/'+bookid)
        # форма выбора жанра
        return render.add_genre(bookid, libdb.get_genres_list())
    POST = GET

class EditBookDelGenrePage:
    def GET(self, bookid, genreid=None):
        check_access('edit_book', bookid)
        i = web.input()
        if 'genreid' in i:
            genreid = i.genreid
        if genreid:
            try:
                libdb.edit_book_del_genre(bookid, genreid)
            except libdb.DBError, err:
                return render.edit_book_error(bookid, u'Ошибка', err)
            session.message = u'Жанр удалён'
            raise web.seeother('/editbook/'+bookid)
        return render.edit_book_error(bookid, u'Ошибка', u'Не найден жанр')
    POST = GET

class EditBookAddSequencePage:
    def GET(self, bookid, sequenceid=None):
        check_access('edit_book', bookid)
        return _add_sequence(bookid, sequenceid)
    POST = GET

class EditBookDelSequencePage:
    def GET(self, bookid, sequenceid=None):
        check_access('edit_book', bookid)
        i = web.input()
        if 'sequenceid' in i:
            sequenceid = i.sequenceid
        if sequenceid:
            try:
                libdb.edit_book_del_sequence(bookid, sequenceid)
            except libdb.DBError, err:
                return render.edit_book_error(bookid, u'Ошибка', err)
            session.message = u'Сериал удалён'
            raise web.seeother('/editbook/'+bookid)
        return render.edit_book_error(bookid, u'Ошибка', u'Не найден сериал')
    POST = GET

class EditBookEditAnnPage:
    def GET(self, bookid):
        check_access('edit_book', bookid)
        ann = None
        i = web.input()
        if 'annotation' in i:
            ann = i.annotation
        if ann:
            if 'astext' in i:
                ann = text2annotation(ann)
            try:
                validate_annotation(ann)
                html = annotation2html(ann)
            except Exception, err:
                err = u'Аннотация не обновлена: '+str(err)
                ann = libdb.book_get_ann(bookid, 'annotation')
                return render.edit_ann(bookid, ann, err)
            libdb.update_book_ann(bookid, ann, html)
            session.message = u'Аннотация обновлена'
            raise web.seeother('/editbook/'+bookid)
        ann = libdb.book_get_ann(bookid, 'annotation')
        return render.edit_ann(bookid, ann)
    POST = GET

class EditBookAddFilePage:
    def GET(self, bookid, fileid=None):
        check_access('edit_book', bookid)
        if  fileid is not None:
            # fileid указан в url
            try:
                libdb.edit_book_add_file(bookid, fileid)
            except libdb.DBError, err:
                return render.edit_book_error(bookid, u'Ошибка', err)
            session.message = u'Файл добавлен'
            raise web.seeother('/editbook/'+bookid)
        i = web.input()
        if 'file' in i:
            # file указан в POST
            # ищем
            files = libdb.edit_book_search_file(bookid, i.file)
            # отдаем страницу со списком найденных
            # files может быть пустым списком, проверяется в шаблоне
            return render.add_file_found(bookid, files)
        # форма поиска
        return render.add_smth(bookid, '/edit_book/', u'Добавить файл',
                               'file', u'Id или заголовок файла:')
    POST = GET

class EditBookJoinPage:
    def GET(self, bookid, otherbookid=None):
        check_access('edit_book', bookid)
        if otherbookid is not None:
            # otherbookid указан в url
            try:
                libdb.edit_book_join_books(bookid, otherbookid)
            except libdb.DBError, err:
                return render.edit_book_error(bookid, u'Ошибка', err)
            session.message = u'Книги объединены'
            raise web.seeother('/editbook/'+otherbookid)
        i = web.input()
        if 'otherbook' in i:
            # otherbook указан в POST
            books = libdb.edit_book_search_book(i.otherbook)
            return render.join_books_found(bookid, books)
        return render.add_smth(bookid, '/edit_book/', u'Объединить книги',
                               'otherbook', u'Id или название книги:')
    POST = GET

class EditBookDelFilePage:
    def GET(self, bookid, fileid=None):
        check_access('edit_book', bookid)
        i = web.input()
        if 'fileid' in i:
            fileid = i.fileid
        if fileid:
            if 'delete' in i:
                # удалить файл
                try:
                    libdb.edit_book_del_file(bookid, fileid)
                except libdb.DBError, err:
                    return render.edit_book_error(bookid, u'Ошибка', err)
                session.message = u'Файл удалён из книги'
                raise web.seeother('/editbook/'+bookid)
            elif 'hide' in i:
                # спрятать/показать
                try:
                    libdb.edit_book_hide_file(bookid, fileid)
                except libdb.DBError, err:
                    return render.edit_book_error(bookid, u'Ошибка', err)
                session.message = u'Изменена видимость файла'
                raise web.seeother('/editbook/'+bookid)
        return render.edit_book_error(bookid, u'Ошибка', u'Непонятное действие')
    POST = GET

## ----------------------------------------------------------------------
## редактирование авторского сериала
## ----------------------------------------------------------------------

class EditSequencePage:
    def GET(self, sequenceid, action=None):
        check_access('edit_sequence', sequenceid)
        sequence = libdb.get_sequence(sequenceid)
        if not sequence:
            raise web.notfound()
        i = web.input()
        if action == 'setname':
            if 'name' not in i:
                return render.edit_sequence_error(sequenceid, u'Ошибка',
                                                  u'Не указано новое имя сериала')
            try:
                libdb.edit_sequence_set_name(sequenceid, i.name)
            except libdb.DBError, err:
                return render.edit_sequence_error(sequenceid, u'Ошибка', err)
            session.message = u'Имя сериала изменено'
            raise web.seeother('/editsequence/'+sequenceid)
        if action == 'delparrent':
            try:
                libdb.edit_sequence_del_parrent(sequenceid)
            except libdb.DBError, err:
                return render.edit_sequence_error(sequenceid, u'Ошибка', err)
            session.message = u'Родительский сериал удалён'
            raise web.seeother('/editsequence/'+sequenceid)
        html = render.edit_sequence(sequence)
        session.message = ''
        return html
    POST = GET

class EditSequenceSetParrentPage:
    def GET(self, sequenceid, parsequenceid=None):
        return render.not_implemented()
        check_access('edit_sequence', sequenceid)
        i = web.input()
        newsequence = False # устанавливается в True, если создан новый сериал
        if 'sequencename' in i:
            if not i.sequencename:
                err = u'Вы не ввели сериал'
                return render.add_sequence(sequenceid, '/editsequence/', err)
            # если такого сериала нет - будет создан
            try:
                sequenceid, newsequence = libdb.edit_sequence_add_sequence(
                    i.sequencename, i.sequencenumber)
            except libdb.DBError, err:
                return render.add_sequence(sequenceid, '/editsequence/', err)
        if sequenceid:
            # успешно
            if newsequence:
                session.message = u'Создан новый сериал.'
            else:
                session.message = u'Сериал добавлен.'
            raise web.seeother(seeother+itemid)
        # форма выбора сериала
        return render.add_sequence(itemid, seeother)
    POST = GET

class EditSequenceSetNumberPage:
    def GET(self, sequenceid, bookid):
        check_access('edit_sequence', sequenceid)
        i = web.input()
        if 'sequencenumber' not in i:
            return render.edit_sequence_error(sequenceid, u'Ошибка',
                                              u'Не указан номер')
        try:
            libdb.edit_sequence_set_number(sequenceid, bookid, i.sequencenumber)
        except libdb.DBError, err:
            return render.edit_sequence_error(sequenceid, u'Ошибка', err)
        session.message = u'Порядковый номер в серии для книги №%s изменён' % bookid
        raise web.seeother('/editsequence/'+sequenceid)
    POST = GET

## ----------------------------------------------------------------------

class EditFilePage:
    def GET(self, fileid):
        check_access('edit_file', fileid)
        file = libdb.get_file(fileid)
        if not file:
            raise web.notfound()
        html = render.edit_file(file)
        session.message = ''            # сбрасываем сообщение
        return html
    POST = GET

class EditFileSetTitlePage:
    def GET(self, fileid, title=None):
        check_access('edit_file', fileid)
        return _set_title(fileid, title, '/editfile/', libdb.edit_file_set_title)
    POST = GET

class EditFileSetYearPage:
    def GET(self, fileid, year=None):
        check_access('edit_file', fileid)
        return _set_year(fileid, year, '/editfile/', libdb.edit_file_set_year)
    POST = GET

class EditFileSetLangPage:
    def GET(self, fileid, lang=None):
        check_access('edit_file', fileid)
        return _set_lang(fileid, lang, '/editfile/', libdb.edit_file_set_lang)
    POST = GET

class EditFileAddTranslatorPage:
    def GET(self, fileid, authorid=None):
        check_access('edit_file', fileid)
        return _add_author(fileid, authorid,
                           seeother='/editfile/',
                           addurl='/addtranslator/',
                           what=u'Переводчик',
                           add_author_func=libdb.edit_file_add_translator)
    POST = GET

class EditFileDelTranslatorPage:
    def GET(self, fileid, authorid=None):
        check_access('edit_file', fileid)
        return _del_author(fileid, authorid,
                           seeother='/editfile/',
                           what=u'Переводчик',
                           del_author_func=libdb.edit_file_del_translator)
    POST = GET

class EditFileAddSequencePage:
    def GET(self, fileid, sequenceid=None):
        check_access('edit_file', fileid)
        return _add_sequence(fileid, sequenceid,
                             publish=True, seeother='/editfile/')
    POST = GET

class EditFileDelSequencePage:
    def GET(self, fileid, sequenceid=None):
        check_access('edit_file', fileid)
        i = web.input()
        if 'sequenceid' in i:
            sequenceid = i.sequenceid
        if sequenceid:
            try:
                libdb.edit_file_del_sequence(fileid, sequenceid)
            except libdb.DBError, err:
                return render.edit_file_error(fileid, u'Ошибка', err)
            session.message = u'Серия удалена'
            raise web.seeother('/editfile/'+fileid)
        return render.edit_file_error(fileid, u'Ошибка', u'Не найдена серия')
    POST = GET

