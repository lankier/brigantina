#!/usr/bin/env python
# -*- mode: python; coding: utf-8; -*-
# (c) Lankier mailto:lankier@gmail.com

db_args = dict(dbn='postgres', db='library', user='con', pw='')
drupal_db_args = dict(dbn='mysql', db='drupal', user='www', pw='a1s2d3')

home_dir = ''
templates_dir = 'templates'
log_file = 'log/brigantina.log'
upload_dir = 'ocr'
books_dir = 'files'
xslt_dir = 'xslt'

filetypes = ('fb2', 'html', 'txt')

schema_dir = 'schema'
schema_file = 'FictionBook2.21.xsd'
annotation_schema_file = 'annotation.xsd'

session_parameters = {
    'cookie_name': 'session_id',
    #'cookie_domain': None,
    #'timeout': (86400,), #24 * 60 * 60, # 24 hours   in seconds
    #'ignore_expiry': True,
    #'ignore_change_ip': True,
    'secret_key': '75938a7e5eda7df8',
    #'expired_message': 'Session expired',
}
# список привилегированных пользователей
admins = ['admin',]
