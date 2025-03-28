#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
전체 실행 순서:
 1) main()에서 명령줄 인자를 파싱한다. (A, B, output_html, XML 파일 목록)
 2) parse_all_files()를 호출해 각 XML 파일을 파싱하고 결과를 수집한다.
 3) build_html()를 호출해 최종 HTML 문서를 생성한다.
 4) 생성된 HTML은 지정된 경로에 저장되며, html_resources 폴더의 리소스도 함께 복사한다.

주요 디자인 개선:
 - 제목(h1, h2, h3)은 왼쪽 정렬
 - File Summary 표: 열 제목 → "Report name", "Total unit tests", "Failure", "Duration", "Timestamp"
 - Test Details by File:
   - 열 제목: "Test name", "Duration", "Result"
   - "Duration" 열은 10ch, "Result" 열은 8ch로 고정 (한 줄로 표시, 넘치면 말줄임)
   - 성공/실패/미실행 아이콘은 모두 가운데 정렬
 - 실패 테스트(.failed)는 배경색 변경 없이, 글자색만 빨간색
 - 파싱 진행 상황은 콘솔에 출력
"""

import sys
import os
import glob
import shutil
from xml.dom.minidom import parse
from xml.parsers.expat import ExpatError
from datetime import datetime

sys.dont_write_bytecode = True

# 새 inline SVG 아이콘 (모던 디자인)
OK_ICON = '''<svg width="16" height="16" viewBox="0 0 24 24" fill="#2ecc71" xmlns="http://www.w3.org/2000/svg"><path d="M9 16.2l-3.5-3.5L4 14.2l5 5 12-12-1.5-1.5z"/></svg>'''
NOTOK_ICON = '''<svg width="16" height="16" viewBox="0 0 24 24" fill="#e74c3c" xmlns="http://www.w3.org/2000/svg"><path d="M12 10.585l4.95-4.95 1.414 1.414L13.414 12l4.95 4.95-1.414 1.414L12 13.414l-4.95 4.95-1.414-1.414L10.586 12 5.636 7.05l1.414-1.414z"/></svg>'''
DISABLE_ICON = '''<svg width="16" height="16" viewBox="0 0 24 24" fill="#95a5a6" xmlns="http://www.w3.org/2000/svg"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm5 11H7v-2h10v2z"/></svg>'''

HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Html report from GTest</title>
    <link rel="stylesheet" type="text/css" href="gtest_report.css">
    <script src="extraScript.js"></script>
</head>
<body>

{topTitle}

<h2>Overall Summary</h2>
<table class="overall_summary">
{overallSummary}
</table>

<h2>File Summary</h2>
<table class="file_summary">
{fileSummary}
</table>

<h2>Test Details by File</h2>
{testDetailsByFile}

</body></html>
"""

FILE_SUMMARY_HEADER = (
    "<tr>"
    "<th>Report name</th>"
    "<th>Total unit tests</th>"
    "<th>Failure</th>"
    "<th>Duration</th>"
    "<th>Timestamp</th>"
    "</tr>\n"
)

class Empty:
    """테스트 상태(아이콘, CSS 등)를 담기 위한 임시 객체."""
    pass

def generate_row(cells, is_header=False, row_style=""):
    tag = "th" if is_header else "td"
    row_html = f'<tr style="{row_style}">'
    for c in cells:
        if isinstance(c, Empty):
            css = getattr(c, 'cssClass', '')
            val = getattr(c, 'value', '')
            row_html += f'<{tag} class="{css}">{val}</{tag}>'
        else:
            row_html += f'<{tag}>{c}</{tag}>'
    row_html += "</tr>\n"
    return row_html

def parse_timestamp(ts_str, storage_list):
    if not ts_str:
        return
    try:
        dt = datetime.strptime(ts_str, "%Y-%m-%dT%H:%M:%S")
        storage_list.append(dt)
    except ValueError:
        pass

def parse_single_file(xml_path):
    print(f"Parsing: {xml_path}")
    try:
        dom = parse(xml_path)
    except ExpatError as e:
        print(f"Failed to parse {xml_path}, reason: {e}")
        return None

    suites_nodes = dom.getElementsByTagName("testsuites")
    if len(suites_nodes) == 0:
        suites_nodes = dom.getElementsByTagName("testsuite")
        if len(suites_nodes) == 0:
            print(f"Warning: No <testsuites> or <testsuite> in {xml_path}")
            return None

    root = suites_nodes[0]
    if root.tagName == "testsuites":
        test_suite_nodes = root.getElementsByTagName("testsuite")
    else:
        test_suite_nodes = [root]

    file_failures = 0
    file_time = 0.0
    file_timestamps = []

    if root.hasAttribute("timestamp"):
        parse_timestamp(root.getAttribute("timestamp"), file_timestamps)
    elif root.hasAttribute("timestamps"):
        parse_timestamp(root.getAttribute("timestamps"), file_timestamps)

    for ts in test_suite_nodes:
        f_attr = ts.getAttribute("failures") or "0"
        t_attr = ts.getAttribute("time") or "0.0"
        try:
            file_failures += int(f_attr)
        except ValueError:
            pass
        try:
            file_time += float(t_attr)
        except ValueError:
            pass
        if ts.hasAttribute("timestamp"):
            parse_timestamp(ts.getAttribute("timestamp"), file_timestamps)
        elif ts.hasAttribute("timestamps"):
            parse_timestamp(ts.getAttribute("timestamps"), file_timestamps)

    testcases = dom.getElementsByTagName("testcase")
    file_test_count = len(testcases)
    file_earliest_ts = min(file_timestamps) if file_timestamps else None

    file_base_name = os.path.basename(xml_path)
    test_details = []

    for tc in testcases:
        classname = tc.getAttribute("classname")
        testname = tc.getAttribute("name")
        full_name = f"{classname}.{testname}"

        t_val = tc.getAttribute("time") or "0.0"
        try:
            exec_time = float(t_val)
        except ValueError:
            exec_time = 0.0

        st = tc.getAttribute("status")
        fails = tc.getElementsByTagName("failure")

        status_obj = Empty()
        if st == "notrun":
            status_obj.value = DISABLE_ICON
            status_obj.cssClass = "notrun"
        elif len(fails) == 0:
            status_obj.value = OK_ICON
            status_obj.cssClass = "run"
        else:
            status_obj.value = NOTOK_ICON
            status_obj.cssClass = "failed"

        extras = ""
        for k, v in tc.attributes.items():
            if k not in ["name", "status", "time", "classname"]:
                extras += f"{k}:{v}\n"
        if extras:
            detail_id = (full_name + "_" + file_base_name).replace(".", "_") + "_detail"
            extra_html = (
                f"<pre>{extras}</pre>"
                f'<input type="image" src="more_button.png" style="float: right;" '
                f'height="30" onclick="ShowDiv(\'{detail_id}\')"></input>'
                f'<div id="{detail_id}" style="display:none;">{extras}</div>'
            )
            status_obj.value += extra_html

        test_details.append((full_name, exec_time, status_obj))

    print(f"Done parse: {xml_path}, testcases: {file_test_count}, failures: {file_failures}")
    return (file_base_name, file_test_count, file_failures, file_time, file_earliest_ts, test_details)

def parse_all_files(files):
    results = []
    total_tests = 0
    total_failures = 0
    all_timestamps = []
    idx = 1
    for xml_path in files:
        file_data = parse_single_file(xml_path)
        if not file_data:
            idx += 1
            continue
        (fname, fTestCount, fFails, fTime, fEarliestTs, testDetails) = file_data
        total_tests += fTestCount
        total_failures += fFails
        if fEarliestTs:
            all_timestamps.append(fEarliestTs)
        results.append((idx, fname, fTestCount, fFails, fTime, fEarliestTs, testDetails))
        idx += 1
    print(f"Finished parsing {len(results)} files")
    return (results, total_tests, total_failures, all_timestamps)

def build_html(A, B, outFile, parse_result):
    (results, total_tests, total_failures, all_ts) = parse_result
    # 제목 왼쪽 정렬
    top_title_html = f'<h1 style="text-align:left;">{A} {B} Report</h1>'

    success_count = total_tests - total_failures
    earliest_ts_str = ""
    if all_ts:
        earliest_ts = min(all_ts)
        earliest_ts_str = earliest_ts.strftime("%Y-%m-%dT%H:%M:%S")

    fail_str = str(total_failures)
    if total_failures > 0:
        fail_str = f'<span style="color:red;">{total_failures}</span>'

    overall_rows = []
    overall_rows.append(generate_row(["Total XML files", len(results)]))
    overall_rows.append(generate_row(["Total tests", total_tests]))
    overall_rows.append(generate_row(["Success tests", success_count]))
    overall_rows.append(generate_row(["Failure tests", fail_str]))
    overall_rows.append(generate_row(["Earliest timestamp", earliest_ts_str]))
    overall_summary_html = "".join(overall_rows)

    # File Summary
    file_summary_rows = []
    for (idx, fname, fTCount, fFails, fTime, fEarliestTs, testDetails) in results:
        if fFails > 0:
            fFails_html = f'<span style="color:red;">{fFails}</span>'
        else:
            fFails_html = str(fFails)
        ts_str = ""
        if fEarliestTs:
            ts_str = fEarliestTs.strftime("%Y-%m-%dT%H:%M:%S")
        link_anchor = f'<a href="#details_{idx}">{fname}</a>'
        row_cells = [link_anchor, fTCount, fFails_html, f"{fTime:.2f}", ts_str]
        file_summary_rows.append(generate_row(row_cells, is_header=False))
    file_summary_html = FILE_SUMMARY_HEADER + "".join(file_summary_rows)

    # Test Details by File
    # Duration -> 12ch, Result -> 9ch
    test_details_list = []
    for (idx, fname, fTCount, fFails, fTime, fEarliestTs, testDetails) in results:
        test_details_list.append(f'<h3 id="details_{idx}" style="text-align:left;">{idx}) {fname}</h3>')
        test_details_list.append('''
<table class="utests" style="width:100%; table-layout: fixed;">
  <colgroup>
    <col style="width: auto;">
    <col style="width: 12ch; overflow: hidden; white-space: nowrap; text-overflow: ellipsis;">
    <col style="width: 9ch; overflow: hidden; white-space: nowrap; text-overflow: ellipsis;">
  </colgroup>
''')
        hdr = generate_row(["Test name", "Duration", "Result"], is_header=True)
        test_details_list.append(hdr)
        for (testName, execTime, stObj) in testDetails:
            row = generate_row([testName, f"{execTime:.2f}", stObj], is_header=False)
            test_details_list.append(row)
        test_details_list.append('</table><br/>\n')
    test_details_html = "".join(test_details_list)

    html_document = HTML_TEMPLATE.format(
        topTitle=top_title_html,
        overallSummary=overall_summary_html,
        fileSummary=file_summary_html,
        testDetailsByFile=test_details_html
    )

    dest_dir = os.path.dirname(outFile)
    if dest_dir and not os.path.isdir(dest_dir):
        os.makedirs(dest_dir)
    with open(outFile, "w", encoding="utf-8") as f:
        f.write(html_document)

def main():
    if len(sys.argv) < 5:
        print("Usage: genHtmlReportFromGtest.py <A> <B> <output_html> <xml1> [xml2 ...]")
        sys.exit(1)

    A = sys.argv[1]
    B = sys.argv[2]
    out_html = sys.argv[3]
    pattern_or_firstxml = sys.argv[4]

    if '*' in pattern_or_firstxml:
        xml_files = glob.glob(pattern_or_firstxml)
    else:
        xml_files = [pattern_or_firstxml] + sys.argv[5:]

    parse_result = parse_all_files(xml_files)
    build_html(A, B, out_html, parse_result)

    dest_dir = os.path.dirname(out_html)
    if not dest_dir:
        dest_dir = "."
    if os.path.isdir("./html_resources"):
        for res in glob.glob("./html_resources/*.*"):
            shutil.copy(res, os.path.join(dest_dir, os.path.basename(res)))

if __name__ == "__main__":
    main()
