#!/usr/bin/env python
# -*- mode: python; coding: utf-8; -*-
# (c) Lankier mailto:lankier@gmail.com
import sys, os
from lxml import etree
from config import schema_dir, schema_file, annotation_schema_file

class ValidationError(Exception):
    pass

def _strip(s):
    return (s
            .replace('{http://www.gribuser.ru/xml/fictionbook/2.0}', '')
            .replace('{http://www.gribuser.ru/xml/fictionbook/2.0/genres}', '')
            )

def get_xsd_dir():
    if os.path.exists(schema_dir):
        return os.path.abspath(schema_dir)
    xsd = None
    for d in sys.path:
        # search dir "schema" in modules path
        sd = os.path.join(d, schema_dir)
        if os.path.exists(sd):
            xsd = sd
            break
    assert xsd, 'xsd dir not found. check your installation'
    return xsd

def get_xsd(schema_file=schema_file):
    if os.path.exists(schema_file):
        return os.path.abspath(schema_file)
    d = os.path.dirname(sys.argv[0])
    f = os.path.join(d, schema_file)
    if os.path.exists(f):
        return f
    return os.path.join(get_xsd_dir(), schema_file)

def check_links(xml, errors):
    numerrors = 0
    href_list = []                      # list of (tag, type, href)
    hrefs = []                          # list of href
    ns = {'xlink':'http://www.w3.org/1999/xlink',
          'l':'http://www.w3.org/1999/xlink'}
    find = etree.XPath("//*[@xlink:href|@l:href]", namespaces=ns)
    for e in find(xml):
        type = e.attrib.get('type')
        txt = e.attrib['{http://www.w3.org/1999/xlink}href']
        href_list.append((e.tag, type, txt, e.sourceline))
        hrefs.append(txt)
    id_list = []                        # list of (tag, id)
    ids = []                            # list of id
    find = etree.XPath("//*[@id]", namespaces=ns)
    for e in find(xml):
        id_list.append((e.tag, e.attrib['id'], e.sourceline))
        ids.append(e.attrib['id'])
    for tag, type, href, line in href_list:
        if not href:
            errors.append('ERROR: line %s: empty link' % line)
            continue
        if not href.startswith('#'):
            if tag.endswith('}image'):
                errors.append('ERROR: line %s: external image: %s' % (line, href))
                numerrors += 1
                continue
            if type == 'note':
                errors.append('ERROR: line %s: external note: %s' % (line, href))
                numerrors += 1
                continue
            if not (href.startswith('http:') or
                    href.startswith('https:') or
                    href.startswith('ftp:') or
                    href.startswith('mailto:')):
                errors.append('ERROR: line %s: bad external link: %s' % (line, href))
                numerrors += 1
                #errors.append('WARNING: local external link:', href)
        elif href[1:] not in ids:
            errors.append('ERROR: line %s: bad internal link: %s' % (line, href))
            numerrors += 1
    for tag, id, line in id_list:
        if tag.endswith('}binary') and '#'+id not in hrefs:
            errors.append('ERROR: line %s: not linked image: %s' % (line, id))
            numerrors += 1
    return numerrors

def check_empty_tags(xml, errors):
    errs = 0
    find = etree.XPath('//*')
    for e in find(xml):
        if (not e.getchildren() and
            not e.tag.endswith('empty-line') and
            not e.tag.endswith('image') and
            not e.tag.endswith('sequence')):
            if e.text is None or not e.text.strip():
                errors.append('WARNING: line %s: empty tag: %s' %
                              (e.sourceline, _strip(e.tag)))
                errs += 1
    return errs

schema = None
def lxml_lint(data, errors, from_str=False):
    global schema
    try:
        if from_str:
            xml = etree.XML(data)
        else:
            xml = etree.parse(data)
    except:
        return None
    if schema is None:
        curdir = os.path.abspath(os.path.curdir)
        xsd = get_xsd()
        os.chdir(os.path.dirname(xsd))
        schema = etree.XMLSchema(etree.XML(open(xsd).read()))
        os.chdir(curdir)
    r = schema.validate(xml)
    if not r:
        #errors.append(u'Ошибки при проверке fb2')
        for s in schema.error_log:
            errors.append('ERROR: line %s: %s' % (s.line, _strip(s.message)))
    return xml

def check_file(fn, errors):
    xml = lxml_lint(fn, errors)
    if xml is None:
        return None
    check_links(xml, errors)
    check_empty_tags(xml, errors)
    return xml

def check_str(data, errors):
    xml = lxml_lint(data, errors, from_str=True)
    if xml is None:
        return None
    check_links(xml, errors)
    check_empty_tags(xml, errors)
    return xml

def validate_annotation(data):
    xml = etree.fromstring(data)
    xsd = os.path.join(schema_dir, annotation_schema_file)
    schema = etree.XMLSchema(etree.parse(xsd))
    r = schema.validate(xml)
    if not r:
        log = []
        for s in schema.error_log:
            log.append('ERROR: line %s: %s;' % (s.line, s.message))
        log = ' '.join(log)
        raise ValidationError, log
    return xml

if __name__ == '__main__':
    errors = []
    check_file(sys.argv[1], errors)
    for e in errors: print e
    #print validate_annotation(open('bad-ann.fb2').read())



