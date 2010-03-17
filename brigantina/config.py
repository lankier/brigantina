#!/usr/bin/env python
# -*- mode: python; coding: utf-8; -*-
# (c) Lankier mailto:lankier@gmail.com

# параметры базы данных
db_args = dict(dbn='postgres', db='library', user='con', pw='')
# связь с друпалом (опционально, если движок не сможет подключиться к базе,
# он будет пускать с любым login+password)
# (не нужен, если используется внутренняя авторизация)
drupal_db_args = dict(dbn='mysql', db='drupal', user='www', pw='a1s2d3')

# тип авторизации
# internal - внутренняя
# drupal - авторизация через друпал
#register_type = 'drupal'
register_type = 'internal'
# подтверждать регистрацию
confirm = {
    'available': True,
    'host': '0.0.0.0:8080',
    'email': 'noreply@localhost.localdomain',
    'subject': 'Подтверждение регистрации',
    'message': '''Для подтверждения регистрации пройдите по ссылке:
%s''',
    }

home_dir = ''                           # пока не используется
templates_dir = 'templates'
log_file = 'log/brigantina.log'
upload_dir = 'ocr'              # куда будут складываться файлы при заливке
                                # (должен быть доступен для записи веб-серверу
books_dir = 'files'             # где хранятся файлы книг
xslt_dir = 'xslt'               # каталог с файлами для xsl-трансформации
data_dir = 'data'               # каталог для доп. файлов

filetypes = ('fb2', 'html', 'txt') # форматы, в которые можно преобразовать fb2

schema_dir = 'schema'                     # каталог с файлами схемы fb2
schema_file = 'FictionBook2.21.xsd'       # имя основного файла схемы
annotation_schema_file = 'annotation.xsd' # для проверки аннотаций

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

# генерировать файлы из fb2 при добавлении
generate_when_adding = True
