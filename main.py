#!/usr/bin/env python
# -*- coding=UTF-8 -*-
# Created at Jun 18 08:46 by BlahGeek@Gmail.com

import sys
if hasattr(sys, 'setdefaultencoding'):
    sys.setdefaultencoding('UTF-8')


import requests
from bs4 import BeautifulSoup
from os import path
from datetime import datetime
from config import EMAIL, PASSWORD, DEVICE
import logging
import sqlite3

db = sqlite3.connect(\
        path.join(path.dirname(path.realpath(__file__)), 'main.db'))
cursor = db.cursor()

session = requests.session()
session.headers.update({'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/27.0.1453.110 Safari/537.36'})

def getFormHiddenData(form):
    ret = dict()
    for i in form.findAll('input', type='hidden'):
        ret[i['name']] = i['value']
    return ret

def login(email, password):
    LOGIN_URL = 'https://www.amazon.com/ap/signin?_encoding=UTF8&openid.assoc_handle=usflex&openid.claimed_id=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0%2Fidentifier_select&openid.identity=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0%2Fidentifier_select&openid.mode=checkid_setup&openid.ns=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0&openid.ns.pape=http%3A%2F%2Fspecs.openid.net%2Fextensions%2Fpape%2F1.0&openid.pape.max_auth_age=0&openid.return_to=https%3A%2F%2Fwww.amazon.com%2Fgp%2Fyourstore%2Fhome%3Fie%3DUTF8%26ref_%3Dgno_signin'
    LOGIN_POST_URL = 'https://www.amazon.com/ap/signin'
    login_page = BeautifulSoup(session.get(LOGIN_URL).text)
    form = login_page.find('form', id='ap_signin_form')
    data = getFormHiddenData(form)
    data.update({'email': email, 'password': password})
    session.post(LOGIN_POST_URL, data)

def getContents():
    URL = 'https://www.amazon.com/gp/digital/fiona/manage/features/order-history/ajax/queryPdocs.html'
    req = session.post(URL, {'offset': 0, 'count': 15, 
        'contentType': 'Personal Document', 'queryToken': 0, 'isAjax': 1})
    return [{'category': i['category'], 'contentName': i['asin']} 
            for i in req.json()['data']['items']]

def deliverContent(content):
    URL = 'https://www.amazon.com/gp/digital/fiona/content-download/fiona-ajax.html/ref=kinw_myk_ro_send'
    content.update({'isAjax': '1', 'deviceID': DEVICE})
    req = session.post(URL, content)
    assert req.json()['data'] == 1

def deliverAll(contents):
    def contentInDB(content):
        try:
            cursor.execute('select * from content where name = "%s"' % content)
        except sqlite3.OperationalError:
            cursor.execute('create table content (name text)')
            return False
        else:
            return False if cursor.fetchone() is None else True

    contents = filter(lambda x: not contentInDB(x['contentName']), contents)
    for content in contents:
        try:
            logging.info('delivering ' + content['contentName'])
            deliverContent(content)
        except:
            logging.error('Error, ignore')
            pass
        else:
            logging.info('Done. Save to db.')
            cursor.execute('insert into content values ("%s")' % content['contentName'])

    db.commit()

if __name__ == '__main__':
    logging.basicConfig(filename=path.join(path.dirname(path.realpath(__file__)), 'main.db'), 
                        level='INFO', 
                        format='%(asctime)s [%(levelname)s] %(message)s')
    login(EMAIL, PASSWORD)
    deliverAll(getContents())
