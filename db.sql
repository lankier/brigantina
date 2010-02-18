--*- coding:utf-8 -*-
--
-- книги
--
drop table if exists books cascade;
create table books (
  id serial,
  title text not null,
  lang text default '',
  year int default 0,
  default_cover text,   -- обложка по умолчанию
  created timestamp default current_timestamp,
  modified timestamp,
  permission int default 0,     -- 0 - полный доступ
  deleted boolean default false,
  needupdate boolean default false,
  primary key (id)
);
-- доп. инф-ция о книге (см. также filesdesc)
drop table if exists booksdesc cascade;
create table booksdesc (
  bookid int not null references books(id),
  annotation text default '',   -- fb2
  annotation_html text default '', -- преобразован в html (кэширование)
  content text default '',
  content_html text default '',
  covers text,                -- обложки добавленные через сайт (имена файлов)
  unique (bookid)
);
-- другие названия книг
drop table if exists alttitles cascade;
create table alttitles (
  id serial,
  bookid int not null references books(id),
  title text default '',
  unique (bookid, title)
);
--
-- файлы
--
drop table if exists files cascade;
create table files (
  id serial,
  title text default '',
  lang text default 'ru',
  year int default 0,
  filetype text not null,
  fileauthor text default '',
  filesize int not null,
  textsize int not null, -- унифицированный размер
                         -- (без разметки в однобайтной кодировке)
                         -- для не-fb2 равен filesize
  fb2id text,
  fb2version float,
  md5 char(32) not null,
  added timestamp default current_timestamp,
  deleted boolean default false,
  deletedtime timestamp,
  permission int default 0,
  librusecid int,
  origext text,        -- оригинальное расширение файла (с точкой, для не fb2)
  filename text,       -- имя файла транслитом (для fb2 без расширения)
  needupdate boolean default false,
  primary key (id),
  unique (md5)
);
drop table if exists booksfiles cascade;
create table booksfiles (
  bookid int not null references books(id),
  fileid int not null references files(id),
  hidden boolean default false, -- показывать ли файл в этой книге
  unique (bookid, fileid)
);
-- доп. инф-ция из fb2
drop table if exists filesdesc cascade;
create table filesdesc (
  fileid int not null references files(id),
  annotation text default '',   -- fb2
  annotation_html text default '', -- преобразован в html (кэширование)
  content text default '',
  content_html text default '',
  description text default '',  -- fb2 description
  covers text,                  -- обложки (имена файлов) (pickled)
  images text,                  -- все изображения (включая обложки) (pickled)
  unique (fileid)
);
--
-- жанры
--
drop table if exists genres cascade;
create table genres (
  id text not null, -- sf, prose, ...
  description text not null, -- название по-русски
  metagenre text not null, -- группа которой принадлежит жанр (по-русски)
  primary key (id)
);
-- старые жанры (из fb2 2.0) и их соответствие новым
drop table if exists oldgenres cascade;
create table oldgenres (
  oldid text not null,
  newid text not null,
  unique (oldid, newid)
);
drop table if exists booksgenres cascade;
create table booksgenres (
  bookid int not null references books(id),
  genreid text not null references genres(id),
  unique (bookid, genreid)
);
--
-- авторы
--
drop table if exists authors cascade;
create table authors (
  id serial,
  firstname text default '',
  middlename text default '',
  lastname text default '',
  nickname text default '',
  fullname text default '', -- полное имя: "first middle last (nick)"
  email text default '',
  homepage text default '',
  created timestamp default current_timestamp,
  permission int default 0,
  deleted boolean default false,
  librusecid int,
  primary key (id)
);
drop table if exists booksauthors cascade;
create table booksauthors (
  bookid int not null references books(id),
  authorid int not null references authors(id),
  unique (bookid, authorid)
);
-- другие имена авторов
drop table if exists authorsaliases cascade;
create table authorsaliases (
  id serial,
  authorid int not null references authors(id),
  firstname text default '',
  middlename text default '',
  lastname text default '',
  nickname text default '',
  librusecid int
);
-- переводчики (связаны с файлами, а не книгами)
drop table if exists bookstranslators cascade;
create table bookstranslators (
  fileid int not null references files(id),
  authorid int not null references authors(id),
  unique (fileid, authorid)
);
-- биографии авторов
drop table if exists authorsdesc cascade;
create table authorsdesc (
  authorid int not null references authors(id),
  body text,
  html text,
  unique (authorid)
);
--
-- сериалы
--
-- авторские сериалы
drop table if exists sequences cascade;
create table sequences (
  id serial,
  name text not null,
  parrent int,                  -- sequenceid родительского сериала (или null)
  root int,                     -- sequenceid самого верхнего сериала
  number int default 0,         -- порядковый номер в родительском сериале
  librusecid int,
  primary key (id),
  unique (name)
);
-- book<->sequence
drop table if exists bookssequences cascade;
create table bookssequences (
  bookid int not null references books(id),
  sequenceid int not null references sequences(id),
  sequencenumber int not null,
  -- parrent int,                  -- sequenceid родительского сериала (или null)
  unique (bookid, sequenceid, sequencenumber)
);
-- издательские серии
drop table if exists publsequences cascade;
create table publsequences (
  id serial,
  name text default '',
  librusecid int,
  primary key (id),
  unique (name)
);
-- связь publsequences <-> files
drop table if exists filessequences cascade;
create table filessequences (
  fileid int not null references files(id),
  sequenceid int not null references publsequences(id),
  sequencenumber int not null,
  parrent int,
  unique (fileid, sequenceid, sequencenumber)
);
--
-- пользователи, сессии и прочее
--
drop table if exists sessions cascade;
create table sessions (
  session_id text unique not null,
  atime timestamp default current_timestamp,
  username text default '',
  message text default '',
  ip inet
);
-- действия по редактированию
drop table if exists actions cascade;
create table actions (
  id serial,
  ctime timestamp default current_timestamp,
  username text default '',
  hideusername boolean default False, -- == true при заливке книги
  action text default '',             -- описание действия
  authorid int,
  bookid int,
  fileid int,
  sequenceid int,
  publsequenceid int,
  genreid text,
  pages text,
  valuechanged boolean default false
);
drop table if exists oldvalues cascade;
create table oldvalues (
  actionid int unique not null references actions(id),
  dumped boolean default false, -- true если сохраняется не текст а объект
  body text,
  str text                      -- строковое представление (если dumped = true)
);
-- ошибки валидации fb2 файлов
drop table if exists fb2errors cascade;
create table fb2errors (
  fileid int not null references files(id),
  numerrors int,
  numwarnings int,
  errors text,
  time timestamp default current_timestamp,
  unique (fileid)
);
-- статистика скачиваний
drop table if exists downloads cascade;
create table downloads (
  fileid int not null references files(id),
  filetype text not null,
  num int default 0,
  unique (fileid, filetype)
);
-- рейтинги пользователей
drop table if exists ratings cascade;
create table ratings (
  id serial,
  bookid int not null references books(id),
  username text not null,
  ctime timestamp default current_timestamp,
  rating int,
  unique (bookid, username)
);
-- сумма и количество оценок для каждой книги
drop table if exists booksratings cascade;
create table booksratings (
  bookid int not null references books(id),
  num int not null,             -- количество оценок
  sum int not null              -- сумма всех оценок
);
drop table if exists reviews cascade;
create table reviews (
  id serial,
  bookid int, -- references books(id),
  fileid int,
  authorid int,
  username text not null,
  ctime timestamp default current_timestamp, -- время создания
  mtime timestamp default current_timestamp, -- время изменения
  body text,
  html text
);
drop table if exists blockedusers cascade;
create table blockedusers (
  username text not null,
  who text not null,
  what text default 'edit',
  reason text default ''
);
drop table if exists watchlist cascade;
create table watchlist (
  id serial,
  username text not null,
  what text not null,           -- значения: 'authorid', 'bookid', ...
  itemid int not null           -- id соответствующего объекта
);
