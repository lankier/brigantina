#!/usr/bin/env python
# -*- mode: python; coding: utf-8; -*-
# (c) Lankier mailto:lankier@gmail.com
import sys, os
from urlparse import urlparse
import zipfile
import web
form = web.form

from config import books_dir
from utils import text2html, mime_type, book_filename, strsize
import libdb
from session import check_access, check_password
import addfile
import upload
import plugins

__books_dir = os.path.basename(books_dir) # FIXME: относительный путь для сервера
pages_urls = (
    '/', 'Index',
    '/('+__books_dir+'/.+)', 'StaticFiles',
    '/upload', 'Upload',
    '/download', 'ManyDownloadPage',
    '/download/(\\d+)/(.+)', 'DownloadPage',
    '/read/(\\d+)', 'ReadPage',
    '/login', 'Login',
    '/logout', 'Logout',
    '/addbook', 'AddBookPage',
    '/addauthor', 'AddAuthorPage',
    '/book/(\\d+)', 'BookPage',
    '/book/(\\d+)/upload', 'BookUploadPage',
    '/bookhistory/(\\d+)', 'BookHistoryPage',
    '/file/(\\d+)', 'FilePage',
    '/file/(\\d+)/desc', 'FileDescPage',
    '/file/(\\d+)/errors', 'FileErrorsPage',
    '/filehistory/(\\d+)', 'FileHistoryPage',
    '/author/(\\d+)', 'AuthorPage',
    '/authorhistory/(\\d+)', 'AuthorHistoryPage',
    '/sequence/(\\d+)', 'SequencePage',
    '/sequencehistory/(\\d+)', 'SequenceHistoryPage',
    '/genre/(.+)', 'GenrePage',
    '/genre', 'AllGenresPage',
    '/recentchanges', 'RecentChangesPage',
    '/viewoldvalue/(\\d+)', 'ViewOldValuePage',
    '/cover/(\\d+)', 'Cover',
    '/booksearch', 'BookSearch',
    '/reviews', 'AllReviewPage',
    '/editreview/(\\d+)', 'EditReviewPage',
    '/deletereview/(\\d+)', 'DeleteReviewPage',
    '/statistics', 'StatisticsPage',
    '/newbooks', 'NewBooksPage',
    '/newfiles', 'NewFilesPage',
    '/user/(.+)/changes', 'UserChangesPage',
    '/user/(.+)/reviews', 'UserReviewsPage',
    '/user/(.+)/ratings', 'UserRatingsPage',
    '/user/(.+)', 'UserPage', # должен быть последним после всех остальных /user/smth
    '/blockuser', 'BlockUserPage',
    '/watch/(.+)/(\\d+)', 'WatchPage',
    '/watchlist', 'WatchListPage',
    '/viewwatchlist', 'ViewWatchListPage',
    '/undo/(\\d+)', 'UndoPage',
    )

class Index:
    def GET(self):
        return render.index()

class StaticFiles:
    '''не нужен если статика отдается через http-server'''
    def GET(self, path):
        if not os.path.isfile(path):
            raise web.notfound()
        mt = mime_type(path)
        web.header('Content-Type', mt)
        fd = open(path, 'rb')
        data = True
        while data:
            data = fd.read(1024)
            yield data

class Cover:
    '''обложки'''
    def GET(self, fileid):
        cover = libdb.get_cover(fileid)
        if not cover:
            raise web.notfound()
        path = os.path.join('/', books_dir, fileid, cover)
        raise web.redirect(path)

class BookPage:
    def GET(self, bookid):
        book = libdb.get_book(bookid)
        if not book:
            raise web.notfound()
        for f in book.files:
            f.textsize = strsize(f.textsize)
        res = libdb.book_get_user_opinion(session.username, bookid)
        book.sum, book.num, book.rating, book.reviews = res
        if book.num:
            book.avg = round(float(book.sum) / book.num, 2)
        else:
            book.avg = 0
        return render.book(book)
    def POST(self, bookid):
        i = web.input()
        if 'rating' in i:
            # голосование
            if not session.username:
                raise web.forbidden(render.forbidden())
            rating = i.rating.strip()
            if rating:
                try:
                    rating = int(rating)
                    assert 1 <= rating <= 10
                except:
                    return render.error(u'Ошибка', u'Неправильный запрос',
                                        '/book/'+bookid)
            libdb.book_set_rating(session.username, bookid, rating)
        if 'review' in i:
            # отзыв
            if not session.username:
                raise web.forbidden(render.forbidden())
            review = i.review.strip()
            html = text2html(review)
            libdb.add_review(username=session.username, bookid=bookid,
                             body=review, html=html)
        return self.GET(bookid)

class EditReviewPage:
    def GET(self, reviewid):
        try:
            review = libdb.get_review(reviewid)
        except IndexError:
            raise web.notfound()
        if review.username != session.username:
            raise web.forbidden(render.forbidden())
        i = web.input()
        if 'review' in i:
            html = text2html(i.review)
            libdb.change_review(reviewid, i.review, html)
            if review.bookid:
                # отзыв о книге
                raise web.seeother('/book/'+str(review.bookid))
            elif review.fileid:
                # отзыв о файле
                raise web.seeother('/file/'+str(review.fileid))
            elif review.authorid:
                # отзыв об авторе
                raise web.seeother('/author/'+str(review.authorid))
            # какая-то ошибка
            raise web.notfound()
        return render.edit_review(review)
    POST = GET

class DeleteReviewPage:
    def GET(self, reviewid):
        try:
            review = libdb.get_review(reviewid)
        except IndexError:
            raise web.notfound()
        if review.username != session.username:
            raise web.forbidden(render.forbidden())
        libdb.delete_review(reviewid)
        if review.bookid:
            # отзыв о книге
            raise web.seeother('/book/'+str(review.bookid))
        elif review.fileid:
            # отзыв о файле
            raise web.seeother('/file/'+str(review.fileid))
        elif review.authorid:
            # отзыв об авторе
            raise web.seeother('/author/'+str(review.authorid))
        raise web.notfound()

class AllReviewPage:
    def GET(self):
        i = web.input()
        page = int(i.get('page', 1))
        reviews, numpages, count = libdb.get_all_reviews(page-1)
        return render.all_reviews(reviews, page, numpages+1)

class AuthorPage:
    def GET(self, authorid):
        author = libdb.get_author(authorid)
        if not author:
            raise web.notfound()
        author.biography = text2html(author.biography)
        author.reviews = libdb.author_get_user_opinion(session.username, authorid)
        return render.author(author)
    def POST(self, authorid):
        i = web.input()
        if 'review' in i:
            if not session.username:
                raise web.forbidden(render.forbidden())
            review = i.review.strip()
            html = text2html(review)
            libdb.add_review(username=session.username, authorid=authorid,
                             body=review, html=html)
        return self.GET(authorid)

class SequencePage:
    def GET(self, sequenceid):
        sequence = libdb.get_sequence(sequenceid)
        if not sequence:
            raise web.notfound()
        return render.sequence(sequence)

class GenrePage:
    def GET(self, genreid):
        i = web.input()
        page = int(i.get('page', 1))
        genre, numpages, count = libdb.get_genre(genreid, page-1)
        if not genre:
            raise web.notfound()
        return render.genre(genre, page, numpages+1, count)

class AllGenresPage:
    def GET(self):
        genres = libdb.get_all_genres()
        return render.all_genres(genres)

class FilePage:
    def GET(self, fileid):
        file = libdb.get_file(fileid)
        if not file:
            raise web.notfound()
        file.reviews = libdb.file_get_user_opinion(session.username, fileid)
        return render.file(file)
    def POST(self, fileid):
        i = web.input()
        if 'review' in i:
            if not session.username:
                raise web.forbidden(render.forbidden())
            review = i.review.strip()
            html = text2html(review)
            libdb.add_review(username=session.username, fileid=fileid,
                             body=review, html=html)
        return self.GET(fileid)

class FileDescPage:
    def GET(self, fileid):
        file = libdb.get_file(fileid)
        if not file:
            raise web.notfound()
        return render.file_description(file)

class FileErrorsPage:
    def GET(self, fileid):
        file = libdb.get_file(fileid)
        if not file:
            raise web.notfound()
        return render.file_errors(file)

## ----------------------------------------------------------------------
## история изменений
## ----------------------------------------------------------------------

def _get_changes(back, page_render, **kwargs):
    i = web.input()
    page = i.get('page', 1)
    try:
        page = int(page)
        assert page > 0
    except:
        return render.error(u'Ошибка', u'Неправильный запрос', back)
    changes, numpages = libdb.get_recent_changes(page-1, **kwargs)
    return page_render(changes, page, numpages+1)

class BookHistoryPage:
    '''история редактирования книги'''
    def page_render(self, changes, page, numpages):
        return render.book_changes(self.bookid, changes, page, numpages)
    def GET(self, bookid):
        self.bookid = bookid
        return _get_changes('/bookhistory/'+bookid, self.page_render,
                            bookid=bookid)

class FileHistoryPage:
    '''история редактирования файла'''
    def page_render(self, changes, page, numpages):
        return render.file_changes(self.fileid, changes, page, numpages)
    def GET(self, fileid):
        self.fileid = fileid
        return _get_changes('/filehistory/'+fileid, self.page_render,
                            fileid=fileid)

class AuthorHistoryPage:
    '''история редактирования автора'''
    def page_render(self, changes, page, numpages):
        return render.author_changes(self.authorid, changes, page, numpages)
    def GET(self, authorid):
        self.authorid = authorid
        return _get_changes('/authorhistory/'+authorid, self.page_render,
                            authorid=authorid)

class SequenceHistoryPage:
    '''история редактирования сериала'''
    def page_render(self, changes, page, numpages):
        return render.sequence_changes(self.sequenceid, changes, page, numpages)
    def GET(self, sequenceid):
        self.sequenceid = sequenceid
        return _get_changes('/sequencehistory/'+sequenceid, self.page_render,
                            sequenceid=sequenceid)

class RecentChangesPage:
    '''все изменения'''
    def GET(self):
        return _get_changes('/recentchanges', render.all_changes)

class UserChangesPage:
    '''правки сделанные пользователем'''
    def page_render(self, changes, page, numpages):
        blocked = libdb.block_user(self.username, action='isblocked')
        return render.user_changes(self.username, blocked,
                                   changes, page, numpages)
    def GET(self, username):
        self.username = username
        return _get_changes('/user/'+username+'/changes', self.page_render,
                            username=username, hideusername=False)

class ViewOldValuePage:
    def GET(self, actionid):
        try:
            oldvalue = libdb.get_oldvalue(actionid)
        except libdb.DBError, err:
            return render.error(u'Ошибка', err)
        return render.view_oldvalue(oldvalue)

class ViewWatchListPage:
    '''показывает список страниц за которыми наблюдает пользователь'''
    def GET(self):
        if not session.username:
            raise web.forbidden(render.forbidden())
        watch_list = libdb.get_watch_list(session.username)
        return render.watch_list(watch_list)

class WatchListPage:
    '''пользовательский список наблюдения'''
    def page_render(self, changes, page, numpages):
        return render.view_changes(changes, page, numpages)
    def GET(self):
        if not session.username:
            raise web.forbidden(render.forbidden())
        watchlist = libdb.get_watched_items(session.username)
        if not watchlist:
            return render.view_changes(None, None, None)
        return _get_changes('/watchlist', self.page_render, watchlist=watchlist)

## ----------------------------------------------------------------------

# NB: не использовать в формах юникод - глючит
login_form = form.Form(
    form.Textbox('username', description='Пользователь'),
    form.Password('password', description='Пароль'),
    form.Button('submit', type='submit', description='Login', html='Отправить'),
    validators= [
        form.Validator('Неправильный пароль или имя пользователя',
                       lambda i: check_password(i.username, i.password))])
class Login:
    def GET(self):
        f = login_form()
        return render.login(f)
    def POST(self):
        f = login_form()
        if not f.validates():
            return render.login(f)
        i = web.input()
        session.username = i.username
        raise web.seeother('/')

class Logout:
    def GET(self):
        session.kill()
        raise web.seeother('/')

class UserPage:
    def GET(self, username):
        return render.user_page(username)

class UserReviewsPage:
    def GET(self, username):
        reviews = libdb.get_user_reviews(username)
        return render.user_reviews(username, reviews)

class UserRatingsPage:
    def GET(self, username):
        return render.not_implemented('/user/'+username)

def _watch_message(what, item, res):
    s = {
        'book': [u'Книга %s удалена из списка наблюдения',
                 u'Книга %s добавлена в список наблюдения'],
        'author': [u'Автор %s удалён из списка наблюдения',
                   u'Автор %s добавлен в список наблюдения'],
        'file': [u'Файл %s удалён из списка наблюдения',
                 u'Файл %s добавлен в список наблюдения'],
        'sequence': [u'Сериал %s удалён из списка наблюдения',
                     u'Сериал %s добавлен в список наблюдения'],
        }
    msg = s[what][res]
    return msg % item

class WatchPage:
    def GET(self, what, itemid):
        if not session.username:
            raise web.forbidden(render.forbidden())
        res = libdb.add_watch(session.username, what, itemid)
        session.message = _watch_message(what, itemid, res)
        #print '*** HTTP_REFERER:', web.ctx.env.get('HTTP_REFERER')
        #back = web.ctx.env.get('HTTP_REFERER')
        #if back:
        #    back = urlparse(back).path
        #if back:
        #    raise web.seeother(back)
        i = web.input()
        if 'back' in i:
            raise web.seeother(i.back)
        raise web.seeother('/'+what+'/'+itemid)

class BlockUserPage:
    def POST(self):
        check_access('admin')
        i = web.input()
        libdb.block_user(i.username, i.reason, session.username, 'edit', i.action)
        back = '/user/%s/changes' % i.username
        if i.action == 'block':
            return render.error(u'Сделано',
                                u'Пользователь %s заблокирован' % i.username,
                                back)
        return render.error(u'Сделано',
                            u'Пользователь %s разблокирован' % i.username,
                            back)

class BookSearch:
    def GET(self):
        i = web.input(q='')
        search = i.q
        res = libdb.book_search(search)
        return render.book_search(search, *res)
    POST = GET

class Upload:
    '''загрузка fb2 файлов'''
    def GET(self):
        check_access('upload')
        return render.upload()

    def POST(self):
        check_access('upload')
        added = upload.upload_fb2()
        return render.upload_page(added)

class BookUploadPage:
    '''загрузка не-fb2 файлов в указанную книгу'''
    def GET(self, bookid):
        check_access('upload')
        return render.upload_other()

    def POST(self, bookid):
        check_access('upload')
        added = upload.upload_other(bookid)
        return render.upload_page(added)

class AddBookPage:
    def GET(self):
        check_access('add_book')
        return render.add_new_book(libdb.get_genres_list())
    def POST(self):
        i = web.input()
        for s in ('title', 'genre', 'firstname', 'lastname'):
            if s not in i or not i[s]:
                return render.add_new_book(libdb.get_genres_list(), i,
                                           u'Все поля обязательны')
        author = dict(firstname=i.firstname, lastname=i.lastname)
        allauthors = [author]
        allgenres = [i.genre]
        bookid, newbook = addfile.add_book(i.title, allauthors, allgenres)
        if newbook:
            session.message = u'Создана новая книга'
        else:
            session.message = u'Такая книга уже существует'
        raise web.seeother('/editbook/'+str(bookid))

class AddAuthorPage:
    def GET(self):
        check_access('add_author')
        return render.add_new_author()
    def POST(self):
        i = web.input()
        for s in ('firstname', 'lastname'):
            if s not in i or not i[s]:
                return render.add_new_author(i, u'Все поля обязательны')
        author = dict(firstname=i.firstname, lastname=i.lastname)
        if i.get('checkuniq', False):
            aids = libdb.find_author(author)
            if aids:
                return render.add_new_author(i, u'Такой автор уже существует')
        authorid = libdb.add_author(author)
        session.message = u'Создан новый автор'
        raise web.seeother('/editauthor/'+str(authorid))

class ManyDownloadPage:
    def POST(self):
        check_access('many_download')
        i = web.input()
        files = []
        for k in i:
            if i[k] != 'on':
                continue
            if k.startswith('file_'):
                fileid = k[5:]
            try:
                fileid = int(fileid)
            except ValueError:
                continue
            files.append(fileid)
        if not files:
            return render.error(u'Ничего не выбрано',
                                u'Список для скачивания пуст',
                                i.get('back'))
        return files

class DownloadPage:
    def GET(self, fileid, filetype):
        check_access('download')
        if filetype == 'orig':
            # не fb2
            path = plugins.other_get(fileid)
        else:
            # fb2
            path = plugins.fb2_get(fileid, filetype)
        if not path:
            raise web.notfound()
        raise web.seeother('/'+path)

class ReadPage:
    def GET(self, fileid):
        ##check_access('download')
        path = plugins.fb2_read(fileid)
        if not path:
            raise web.notfound()
        raise web.seeother('/'+path)

class StatisticsPage:
    def GET(self):
        stat = libdb.get_statistics()
        return render.statistics(stat)

class UndoPage:
    def POST(self, actionid):
        i = web.input()
        back = i.get('back')
        try:
            libdb.undo(actionid)
        except libdb.DBError, err:
            return render.error(u'Ошибка', err, back)
        if back:
            web.seeother(back)
        return 'OK'

class NewBooksPage:
    def GET(self):
        i = web.input()
        page = int(i.get('page', 1))
        newbooks, numpages = libdb.get_new_books(page-1)
        return render.new_books(newbooks, page, numpages+1)

class NewFilesPage:
    def GET(self):
        i = web.input()
        page = int(i.get('page', 1))
        newfiles, numpages = libdb.get_new_files(page-1)
        return render.new_files(newfiles, page, numpages+1)

