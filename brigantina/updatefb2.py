#!/usr/bin/env python
# -*- mode: python; coding: utf-8; -*-
# (c) Lankier mailto:lankier@gmail.com
import sys, os, time
from copy import deepcopy
from lxml import etree

import libdb
_db = libdb._db
from utils import strtime

namespaces = {'m': 'http://www.gribuser.ru/xml/fictionbook/2.0',
              'xlink':'http://www.w3.org/1999/xlink',
              'l':'http://www.w3.org/1999/xlink'}
def xpath(path):
    find = etree.XPath(path, namespaces=namespaces)
    return find

xp_prefix = '/m:FictionBook/m:description/m:title-info/m:'

def add_authors(new_ti, table, bookid, elem_name, add_unknown=False):
    authors = []
    where = 'authors.id = %s.authorid and %s.bookid = $bookid' % (table,table)
    res = list(_db.select(table+', authors', locals(), where=where))
    if res:
        for a in res:
            author = etree.Element(elem_name)
            aut = []
            for e in ('first-name', 'middle-name', 'last-name',
                      'nickname', 'home-page', 'email'):
                name = e.replace('-', '')
                if a[name]:
                    elem = etree.Element(e)
                    elem.text = a[name]
                    author.append(elem)
                    aut.append(a[name])
                else:
                    aut.append('')
            new_ti.append(author)
            authors.append(aut)
    elif add_unknown:
        author = etree.Element(elem_name)
        elem = etree.Element('last-name')
        elem.text = u'Автор неизвестен'
        author.append(elem)
        new_ti.append(author)
        authors.append(['', '', u'Автор неизвестен', ''])
    return authors

def update_fb2(path, book, fileid):
    def copy_elem(elem):
        # just copy old elements
        find = xpath(xp_prefix+elem)
        for e in find(xml):
            new_ti.append(deepcopy(e))
    #
    xml = etree.parse(path)
    # 2. xml
    find = xpath('/m:FictionBook/m:description/m:title-info')
    old_ti = find(xml)[0]                # old <title-info>
    new_ti = etree.Element('title-info') # new <title-info>
    #
    # generation <title-info>
    # 1. <genre>
    res = list(_db.select('genres, booksgenres', locals(),
                          where='booksgenres.bookid = $book.id and genres.id = booksgenres.genreid',
                          what='genres.*'))
    if res:
        for g in res:
            name = g.id
            genre = etree.Element('genre')
            genre.text = name
            new_ti.append(genre)
    else:
        genre = etree.Element('genre')
        genre.text = 'other'
        new_ti.append(genre)
    # 2. <author>
    add_authors(new_ti, 'booksauthors', book.id, 'author', add_unknown=True)
    # 3. <book-title>
    title_text = book.title.strip()
    title = etree.Element('book-title')
    title.text = title_text
    new_ti.append(title)
    # 4. <annotation>
    if book.annotation:
        ann = etree.fromstring(book.annotation)
        new_ti.append(ann)
    # 5. <keywords>
    copy_elem('keywords')
    # 6. <date>
    year_text = str(book.year)
    if year_text:
        year = etree.Element('date')
        year.text = year_text
        new_ti.append(year)
    # 7. <coverpage>
    copy_elem('coverpage')
    # 8. <lang>
    lang_text = book.publlang.lower()
    if lang_text:
        lang = etree.Element('lang')
        lang.text = lang_text
        new_ti.append(lang)
    # 9. <src-lang>
    lang_text = book.lang.lower()
    if lang_text:
        lang = etree.Element('src-lang')
        lang.text = lang_text
        new_ti.append(lang)
    # 10. <translator>
    add_authors(new_ti, 'bookstranslators', book.id, 'translator',
                add_unknown=False)
    # 11. <sequence>
    res = _db.select('sequences, bookssequences',
                     locals(),
                     where='bookssequences.bookid = $book.id and sequences.id = bookssequences.sequenceid',
                     what='sequences.name, bookssequences.sequencenumber')
    for seq in res:
        sequence = etree.Element('sequence')
        sequence.attrib['name'] = seq.name
        sequence.attrib['number'] = str(seq.sequencenumber)
        new_ti.append(sequence)
    # finalisation
    # 1. replace <title-info>
    find = xpath('/m:FictionBook/m:description')
    desc = find(xml)[0]
    desc.replace(old_ti, new_ti)
    # 2. add/update <custom-info>
    library = 'flibusta'
    updater = 'brigantina'
    added_time = strtime(book.created, 'sec')
    update_time = time.strftime('%Y-%m-%d %H:%M:%S')
    #update_time = strtime(book.modified, 'sec')
    bookid_found = False
    fileid_found = False
    added_time_found = False
    update_time_found = False
    updater_found = False
    find = xpath('/m:FictionBook/m:description/m:custom-info')
    for ci in find(xml):
        it = ci.get('info-type')
        if not it:
            if it is None:
                pass
                #print_log('WARNING: <custom-info> has no attribute "info-type"')
        elif it == library+'-book-id':
            bookid_found = True
        elif it == library+'-file-id':
            fileid_found = True
        elif it == library+'-added-at':
            ci.text = added_time
            added_time_found = True
        elif it == library+'-updated-at':
            ci.text = update_time
            update_time_found = True
        elif it == library+'-updater' and ci.text == updater:
            updater_found = True
    if not bookid_found:
        ci = etree.Element('custom-info')
        ci.attrib['info-type'] = library+'-book-id'
        ci.text = str(book.id)
        desc.append(ci)
    if not fileid_found:
        ci = etree.Element('custom-info')
        ci.attrib['info-type'] = library+'-file-id'
        ci.text = str(fileid)
        desc.append(ci)
    if not added_time_found:
        ci = etree.Element('custom-info')
        ci.attrib['info-type'] = library+'-added-at'
        ci.text = added_time
        desc.append(ci)
    if not update_time_found:
        ci = etree.Element('custom-info')
        ci.attrib['info-type'] = library+'-updated-at'
        ci.text = update_time
        desc.append(ci)
    if not updater_found:
        ci = etree.Element('custom-info')
        ci.attrib['info-type'] = library+'-updater'
        ci.text = updater
        desc.append(ci)

    # done
    return etree.tostring(xml, encoding='utf-8', xml_declaration=True)

if __name__ == '__main__':
    bookid = 5
    fileid = 4
    book = libdb.get_book(bookid)
    t = update_fb2('oskolok.fb2', book, fileid)
    open('out.fb2', 'w').write(t)

