#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Google Test XML → HTML 보고서 생성 스크립트
- CSS/JS/Icon 모두 html_resources 하위에서 로드
- 결과 폴더에 html_resources 전체 복사
- 결과 셀에는 성공/실패/스킵 아이콘만 표시
"""

import sys
import os
import glob
import shutil
from xml.dom.minidom import parse
from xml.parsers.expat import ExpatError
from datetime import datetime

sys.dont_write_bytecode = True

# -------------------------------------------------------------------
# 아이콘 정의 (html_resources 폴더 안의 실제 파일명 참조)
OK_ICON    = '<img src="html_resources/gtest_report_ok.png"    alt="OK"      class="icon" width="16" height="16"/>'
NOTOK_ICON = '<img src="html_resources/gtest_report_notok.png" alt="Failure" class="icon" width="16" height="16"/>'
SKIP_ICON  = '<img src="html_resources/gtest_report_disable.png" alt="Skipped" class="icon" width="16" height="16"/>'
# -------------------------------------------------------------------

HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Html report from GTest</title>
    <!-- CSS/JS 모두 html_resources 하위에서 로드 -->
    <link rel="stylesheet" type="text/css" href="html_resources/gtest_report.css">
    <script src="html_resources/extraScript.js"></script>
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

</body>
</html>
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

    suites = dom.getElementsByTagName("testsuites") or dom.getElementsByTagName("testsuite")
    if not suites:
        print(f"Warning: No <testsuites> or <testsuite> in {xml_path}")
        return None
    root = suites[0]
    suite_nodes = root.getElementsByTagName("testsuite") if root.tagName == "testsuites" else [root]

    file_failures   = 0
    file_time       = 0.0
    file_timestamps = []
    file_skipped    = 0

    if root.hasAttribute("timestamp"):
        parse_timestamp(root.getAttribute("timestamp"), file_timestamps)

    for ts in suite_nodes:
        try: file_failures += int(ts.getAttribute("failures") or 0)
        except: pass
        try: file_time     += float(ts.getAttribute("time") or 0.0)
        except: pass
        if ts.hasAttribute("timestamp"):
            parse_timestamp(ts.getAttribute("timestamp"), file_timestamps)

    testcases       = dom.getElementsByTagName("testcase")
    file_test_count = len(testcases)
    file_earliest_ts= min(file_timestamps) if file_timestamps else None
    file_base_name  = os.path.basename(xml_path)
    test_details    = []

    for tc in testcases:
        classname = tc.getAttribute("classname")
        testname  = tc.getAttribute("name")
        full_name = f"{classname}.{testname}"
        try:
            exec_time = float(tc.getAttribute("time") or 0.0)
        except:
            exec_time = 0.0

        status_obj = Empty()
        # 스킵 우선
        if tc.getElementsByTagName("skipped"):
            status_obj.value    = SKIP_ICON
            status_obj.cssClass = "notrun"
            file_skipped       += 1
        elif tc.getElementsByTagName("failure"):
            status_obj.value    = NOTOK_ICON
            status_obj.cssClass = "failed"
        else:
            status_obj.value    = OK_ICON
            status_obj.cssClass = "run"

        # extras 제거: 결과 셀에는 아이콘만 표시
        test_details.append((full_name, exec_time, status_obj))

    print(f"Done parse: {xml_path} (tests={file_test_count}, fails={file_failures}, skipped={file_skipped})")
    return (file_base_name, file_test_count, file_failures, file_skipped, file_time, file_earliest_ts, test_details)

def parse_all_files(files):
    results        = []
    total_tests    = total_failures = total_skipped = 0
    all_timestamps = []
    idx = 1

    for xml in files:
        data = parse_single_file(xml)
        if not data:
            idx += 1
            continue
        fname, cnt, fails, skipped, ttime, ts, details = data
        total_tests    += cnt
        total_failures += fails
        total_skipped  += skipped
        if ts:
            all_timestamps.append(ts)
        results.append((idx, fname, cnt, fails, skipped, ttime, ts, details))
        idx += 1

    print(f"Finished parsing {len(results)} files")
    return results, total_tests, total_failures, total_skipped, all_timestamps

def build_html(A, B, outFile, parse_result):
    results, total, fails, skipped, all_ts = parse_result
    top_title = f'<h1 style="text-align:left;">{A} {B} Report</h1>'

    executed    = total - skipped
    success_cnt = executed - fails
    earliest_ts = min(all_ts).strftime("%Y-%m-%dT%H:%M:%S") if all_ts else ""

    overall_rows = [
        generate_row(["Total XML files", len(results)]),
        generate_row(["Total tests", total]),
        generate_row(["Executed tests", executed]),
        generate_row(["Success tests", success_cnt]),
        generate_row(["Failure tests", fails]),
        generate_row(["Skipped tests", skipped]),
        generate_row(["Earliest timestamp", earliest_ts])
    ]
    overallSummary = "".join(overall_rows)

    file_rows = []
    for idx, fname, cnt, fails, skipped_f, duration, ts, _ in results:
        fails_html = f'<span style="color:red;">{fails}</span>' if fails else "0"
        ts_str     = ts.strftime("%Y-%m-%dT%H:%M:%S") if ts else ""
        link       = f'<a href="#details_{idx}">{fname}</a>'
        file_rows.append(generate_row([link, cnt, fails_html, f"{duration:.2f}", ts_str]))
    fileSummary = FILE_SUMMARY_HEADER + "".join(file_rows)

    detail_html = []
    for idx, fname, *_ , details in results:
        detail_html.append(f'<h3 id="details_{idx}" style="text-align:left;">{idx}) {fname}</h3>')
        detail_html.append("""
<table class="utests" style="width:100%; table-layout:fixed;">
 <colgroup>
   <col style="width:auto;">
   <col style="width:12ch;">
   <col style="width:9ch;">
 </colgroup>
""")
        detail_html.append(generate_row(["Test name", "Duration", "Result"], is_header=True))
        for name, ttime, status in details:
            detail_html.append(generate_row([name, f"{ttime:.2f}", status]))
        detail_html.append("</table><br/>\n")
    testDetailsByFile = "".join(detail_html)

    html = HTML_TEMPLATE.format(
        topTitle=top_title,
        overallSummary=overallSummary,
        fileSummary=fileSummary,
        testDetailsByFile=testDetailsByFile
    )

    out_dir = os.path.dirname(outFile) or "."
    os.makedirs(out_dir, exist_ok=True)
    with open(outFile, "w", encoding="utf-8") as f:
        f.write(html)

    # html_resources 전체를 결과 폴더로 복사
    src_res = "./html_resources"
    dst_res = os.path.join(out_dir, "html_resources")
    if os.path.isdir(src_res):
        shutil.copytree(src_res, dst_res, dirs_exist_ok=True)

def main():
    if len(sys.argv) < 5:
        print("Usage: genHtmlReportFromGtest.py <A> <B> <output_html> <xml1> [xml2 ...]")
        sys.exit(1)
    A, B, out_html = sys.argv[1], sys.argv[2], sys.argv[3]
    pattern        = sys.argv[4]
    xmls           = glob.glob(pattern) if '*' in pattern else [pattern] + sys.argv[5:]
    result         = parse_all_files(xmls)
    build_html(A, B, out_html, result)

if __name__ == "__main__":
    main()
