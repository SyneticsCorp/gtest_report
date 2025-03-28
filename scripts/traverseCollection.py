#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
sys.dont_write_bytecode = True

def extractCssClass(ctr):
    # Special process of css enable case
    cssClass = ""
    if hasattr(ctr, "cssClass"):
        cssClass = ctr.cssClass
        del ctr.cssClass
        fields = {
            field: value
            for field, value in ctr.__dict__.items()
            if not callable(getattr(ctr, field))
        }
        vals = list(fields.values())  # Python 3에서는 list()로 감싸야 인덱싱 가능
        if len(vals) != 1:
            raise Exception("Problems cssClass field can be applied only for class with two fields")
        ctr = vals[0]

    return (cssClass, ctr)

def genRows(ctr, cssClass, expandTypeIsRow):
    res = ""
    for i in ctr:
        newCssClass, i = extractCssClass(i)
        # extractCssClass 반환값을 덮어쓰는 것이 맞음
        # (기존 코드가 cssClass, i를 재할당하는 형태였으므로 동일하게 유지)
        if newCssClass != "":
            res += f'<tr class="{newCssClass}">\n'
        else:
            res += "<tr>\n"

        res += generateElements(i, not expandTypeIsRow)
        res += "\n</tr>\n"
    return res

def genColumns(ctr, cssClass, expandTypeIsRow):
    res = ""
    for i in ctr:
        newCssClass, i = extractCssClass(i)
        if newCssClass != "":
            res += f'<td class="{newCssClass}">'
        else:
            res += "<td>"
        res += generateElements(i, not expandTypeIsRow)
        res += "</td>"
    return res

def genIterative(ctr, cssClass, expandTypeIsRow):
    if expandTypeIsRow == 1:
        return genRows(ctr, cssClass, expandTypeIsRow)
    else:
        return genColumns(ctr, cssClass, expandTypeIsRow)

def generateElements(ctr, expandTypeIsRow):
    xRes = ""
    cssClass, ctr = extractCssClass(ctr)

    if isinstance(ctr, (list, tuple)):
        # Python 2: map(None, ctr) 형태 사용 → 바로 그냥 genIterative(ctr, ...) 호출
        xRes = genIterative(ctr, "", expandTypeIsRow)
    elif isinstance(ctr, dict):
        # Python 2: map(None, ctr.keys(), ctr.values())
        # Python 3에서는 zip(ctr.keys(), ctr.values()) 사용
        # dict는 key/value 개수가 동일하므로 zip만으로 충분
        xRes = genIterative(list(zip(ctr.keys(), ctr.values())), cssClass, expandTypeIsRow)
    elif hasattr(ctr, "__dict__"):
        # fields도 마찬가지
        fields = {
            field: value
            for field, value in ctr.__dict__.items()
            if not callable(getattr(ctr, field))
        }
        kv = list(zip(fields.keys(), fields.values()))
        xRes = genIterative(kv, cssClass, expandTypeIsRow)
    else:
        if not expandTypeIsRow:
            xRes = "<td>" + str(ctr) + "</td>"
        else:
            xRes = str(ctr)

    return xRes

def generateHtmlDocument(ctr):
    htmlDocumentText = '''<!DOCTYPE html>
<html>
<head> <title>Html report from gtest</title> </head>
<body>
{ctr}
</body></html>'''
    return htmlDocumentText.format(ctr=generateElements(ctr, True))

if __name__ == '__main__':
    class A:
        pass

    a = A()
    a.values = [1, 2, 3, 4, None]
    a.cssClass = "wow"
    # Python 3: print 함수를 반드시 써야 함
    print(generateHtmlDocument(a))
