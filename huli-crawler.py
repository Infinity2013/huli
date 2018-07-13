#!/usr/bin/env python
# -*- coding: utf-8 -*-  

from uiautomator import Device
import BeautifulSoup
import re
import operator
import sqlite3
import hashlib
import time




def getPos(tag):
    bounds = tag.get('bounds')
    bounds = map(int, re.findall(r'\d+', bounds))
    posX = (bounds[0] + bounds[2]) / 2
    posY = (bounds[1] + bounds[3]) / 2
    return posX, posY


def findKeyTag(bs):
    nodes = bs.findAll('node')
    tagList = []
    for node in nodes:
        if isinstance(node, BeautifulSoup.Tag) and node.get('text') != '':
            tagList.append([node, getPos(node)[1]])
    tagList = sorted(tagList, key=operator.itemgetter(1))
    title, confirm, ans, report = None, None, None, None
    for i in range(len(tagList)):
        tagItem = tagList[i]
        tag = tagItem[0]
        if u'选题' in getText(tag):
            title = i
        elif u'正确答案' in getText(tag):
            ans = i
        elif u'报错' in getText(tag):
            report = i
            break
    for i in range(report, 0, -1):
        if tagList[i][1] < tagList[report][1]:
            confirm = i
            break
    optionList = []
    for i in range(title + 1, ans if ans is not None else confirm):
        g = re.match(r'\d+\.$', getText(tagList[i][0]))
        if g is not None:
            continue
        optionList.append(tagList[i][0])
    return tagList[title][0], optionList, None if ans is None else tagList[ans][0], tagList[confirm][0]


def getText(tag):
    return tag.get('text').replace('"', '#')


def genHash(title, options):
    textList = []
    textList.append(getText(title))
    for option in options:
        textList.append(getText(option))
    text = ",".join(textList).encode('raw_unicode_escape')
    textHash = hashlib.md5(text).hexdigest()
    return textHash


def parseAns(options, ans):
    g = re.findall('\w', getText(ans))
    right = g[0]
    index = ord(right) - ord('A')
    return getText(options[index])

def dumpPage(d):
    src = d.dump()
    return BeautifulSoup.BeautifulSoup(src)


def click(tag, d):
    bounds = tag.get('bounds')
    bounds = map(int, re.findall(r'\d+', bounds))
    posX = (bounds[0] + bounds[2]) / 2
    posY = (bounds[1] + bounds[3]) / 2
    d.click(posX, posY)


def checkExit(d):
    bs = dumpPage(d)
    confirm = None
    isExit = False
    for node in bs.findAll('node'):
        if u'确 定' in getText(node):
            confirm = node
            isExit = True
            break
    if isExit:
        click(confirm, d)
    return isExit


def clickEntry(d, name):
    bs = dumpPage(d)
    entry = None
    for node in bs.findAll('node'):
        if name in getText(node):
            entry = node
            break
    click(entry, d)


def waitForEntry(d, name):
    entry = None
    while entry is None:
        bs = dumpPage(d)
        for node in bs.findAll('node'):
            if name in getText(node):
                entry = node
                break
        if entry is None:
            time.sleep(2)

            def crawler(d):
                bs = dumpPage(d)
                title, options, _, confirm = findKeyTag(bs)
                queryHash = genHash(title, options)
                queryCmd = 'select * from ' + table + ' where hash="%s"' % queryHash
                localCursor = cursor.execute(queryCmd)
                res = localCursor.fetchone()
                if res is None:
                    click(options[0], d)
                    time.sleep(1)
                    click(confirm, d)
                else:
                    rightText = res[-1]
                    for option in options:
                        if rightText == getText(option):
                            click(option, d)
                            break
                    time.sleep(1)
                    click(confirm, d)

                bs = dumpPage(d)
                title, options, ans, confirm = findKeyTag(bs)
                titleText = getText(title)
                ansText = parseAns(options, ans)
                optionText = "|".join([getText(option) for option in options])
                insertCmd = 'insert or ignore into ' + table + '(hash, title, options, ans) values("%s", "%s", "%s", "%s")' % (
                queryHash, titleText, optionText, ansText)
                cursor.execute(insertCmd)

                db.commit()
                click(confirm, d)


def crawler(d):
    bs = dumpPage(d)
    title, options, _, confirm = findKeyTag(bs)
    queryHash = genHash(title, options)
    queryCmd = 'select * from ' + table + ' where hash="%s"' % queryHash
    localCursor = cursor.execute(queryCmd)
    res = localCursor.fetchone()
    if res is None:
        click(options[0], d)
        time.sleep(1)
        click(confirm, d)
    else:
        rightText = res[-1]
        for option in options:
            if rightText == getText(option):
                click(option, d)
                break
        time.sleep(1)
        click(confirm, d)

    bs = dumpPage(d)
    title, options, ans, confirm = findKeyTag(bs)
    titleText = getText(title)
    ansText = parseAns(options, ans)
    optionText = "|".join([getText(option) for option in options])
    insertCmd = 'insert or ignore into ' + table +'(hash, title, options, ans) values("%s", "%s", "%s", "%s")' % (queryHash, titleText, optionText, ansText)
    cursor.execute(insertCmd)

    db.commit()
    click(confirm, d)

d = Device()
db = sqlite3.connect('nurse-asistant.db')
cursor = db.cursor()
cursor.execute('create table if not exists n4n5(hash varchar[255] primary key, title varchar[255], options varchar[255], ans varchar[255])')
cursor.execute('create table if not exists n1n3(hash varchar[255] primary key, title varchar[255], options varchar[255], ans varchar[255])')
cursor.execute('create table if not exists n6(hash varchar[255] primary key, title varchar[255], options varchar[255], ans varchar[255])')



table = 'n6'
while True:
    res = checkExit(d)
    if res:
        waitForEntry(d, u'开始练习')
        clickEntry(d, u'开始练习')
        waitForEntry(d, u'报错')
    crawler(d)
