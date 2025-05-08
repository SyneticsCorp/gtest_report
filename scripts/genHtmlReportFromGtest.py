#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
전체 실행 순서:
 1) main()에서 명령줄 인자를 파싱한다. (A, B, output_html, XML 파일 목록)
 2) parse_all_files()를 호출해 각 XML 파일을 파싱하고 결과(통과/실패/스킵 등)를 수집한다.
 3) build_html()를 호출해 최종 HTML 문서를 생성한다.
 4) 생성된 HTML은 지정된 경로에 저장되며, html_resources 폴더의 리소스도 함께 복사한다.
"""

import sys
import os
import glob
import shutil
from xml.dom.minidom import parse
from xml.parsers.expat import ExpatError
from datetime import datetime

sys.dont_write_bytecode = True

# SVG 아이콘
OK_ICON = '''<svg width="16" height="16" viewBox="0 0 24 24" ...></svg>'''
NOTOK_ICON = '''<svg width="16" height="16" viewBox="0 0 24 24" ...></svg>'''
SKIP_ICON = '''<svg width="16" height="16" viewBox="0 0 24 24" ...></svg>'''

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

    # <testsuites> 또는 <testsuite> 루트 찾기
    suites = dom.getElementsByTagName("testsuites")
    if not suites:
        suites = dom.getElementsByTagName("testsuite")
    if not suites:
        print(f"Warning: No <testsuites> or <testsuite> in {xml_path}")
        return None
    root = suites[0]
    if root.tagName == "testsuites":
        suite_nodes = root.getElementsByTagName("testsuite")
    else:
        suite_nodes = [root]

    # 파일 단위 통계 초기화
    file_failures = 0
    file_time = 0.0
    file_timestamps = []
    file_skipped = 0

    # timestamp 속성 파싱
    if root.hasAttribute("timestamp"):
        parse_timestamp(root.getAttribute("timestamp"), file_timestamps)
    elif root.hasAttribute("timestamps"):
        parse_timestamp(root.getAttribute("timestamps"), file_timestamps)

    for ts in suite_nodes:
        # failures, time 집계
        f_attr = ts.getAttribute("failures") or "0"
        t_attr = ts.getAttribute("time") or "0.0"
        try: file_failures += int(f_attr)
        except: pass
        try: file_time += float(t_attr)
        except: pass
        # 각 suite timestamp
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
        # 기본 정보
        classname = tc.getAttribute("classname")
        testname = tc.getAttribute("name")
        full_name = f"{classname}.{testname}"
        # 실행 시간
        t_val = tc.getAttribute("time") or "0.0"
        try: exec_time = float(t_val)
        except: exec_time = 0.0

        # 상태 결정
        status_obj = Empty()
        # 스킵 노드가 있으면 우선 처리
        skipped_nodes = tc.getElementsByTagName("skipped")
        if skipped_nodes:
            status_obj.value = SKIP_ICON
            status_obj.cssClass = "skipped"
            file_skipped += 1
        else:
            fails = tc.getElementsByTagName("failure")
            if len(fails) == 0:
                status_obj.value = OK_ICON
                status_obj.cssClass = "run"
            else:
                status_obj.value = NOTOK_ICON
                status_obj.cssClass = "failed"

        # 상세 정보 전용 영역 (스킵 사유 + 기타 속성)
        extras = ""
        if skipped_nodes:
            reason = skipped_nodes[0].getAttribute("message")
            if reason:
                extras += f"Skipped reason: {reason}\n"

        # <testcase> 속성 중 name, status, time, classname 제외한 나머지
        for k, v in tc.attributes.items():
            if k not in ["name", "status", "time", "classname"]:
                extras += f"{k}: {v}\n"

        # 토글 가능한 상세 뷰로 추가
        if extras:
            detail_id = (full_name + "_" + file_base_name).replace(".", "_") + "_detail"
            extra_html = (
                f"<pre>{extras}</pre>"
                f'<input type="image" src="more_button.png" style="float:right;" height="30" '
                f'onclick="ShowDiv(\'{detail_id}\')"></input>'
                f'<div id="{detail_id}" style="display:none;">{extras}</div>'
            )
            status_obj.value += extra_html

        test_details.append((full_name, exec_time, status_obj))

    print(f"Done parse: {xml_path}, tests: {file_test_count}, failures: {file_failures}, skipped: {file_skipped}")
    return (file_base_name, file_test_count, file_failures, file_skipped, file_time, file_earliest_ts, test_details)

def parse_all_files(files):
    results = []
    total_tests = 0
    total_failures = 0
    total_skipped = 0
    all_timestamps = []
    idx = 1

    for xml_path in files:
        data = parse_single_file(xml_path)
        if not data:
            idx += 1
            continue
        (fname, fCount, fFails, fSkipped, fTime, fTs, details) = data
        total_tests    += fCount
        total_failures += fFails
        total_skipped  += fSkipped
        if fTs:
            all_timestamps.append(fTs)
        results.append((idx, fname, fCount, fFails, fSkipped, fTime, fTs, details))
        idx += 1

    print(f"Finished parsing {len(results)} files")
    return (results, total_tests, total_failures, total_skipped, all_timestamps)

def build_html(A, B, outFile, parse_result):
    (results, total_tests, total_failures, total_skipped, all_ts) = parse_result

    # 상단 제목
    top_title_html = f'<h1 style="text-align:left;">{A} {B} Report</h1>'

    # 통계 계산
    executed = total_tests - total_skipped
    success_count = executed - total_failures
    earliest_ts_str = ""
    if all_ts:
        earliest_ts_str = min(all_ts).strftime("%Y-%m-%dT%H:%M:%S")

    # Overall Summary
    overall_rows = []
    overall_rows.append(generate_row(["Total XML files", len(results)]))
    overall_rows.append(generate_row(["Total tests", total_tests]))
    overall_rows.append(generate_row(["Executed tests", executed]))
    overall_rows.append(generate_row(["Success tests", success_count]))
    overall_rows.append(generate_row(["Failure tests", total_failures]))
    overall_rows.append(generate_row(["Skipped tests", total_skipped]))
    overall_rows.append(generate_row(["Earliest timestamp", earliest_ts_str]))
    overall_summary_html = "".join(overall_rows)

    # File Summary (기존 형식 유지)
    file_summary_rows = []
    for (idx, fname, fCount, fFails, fSkipped, fTime, fTs, details) in results:
        fFails_html = f'<span style="color:red;">{fFails}</span>' if fFails > 0 else str(fFails)
        ts_str = fTs.strftime("%Y-%m-%dT%H:%M:%S") if fTs else ""
        link = f'<a href="#details_{idx}">{fname}</a>'
        row_cells = [link, fCount, fFails_html, f"{fTime:.2f}", ts_str]
        file_summary_rows.append(generate_row(row_cells, is_header=False))
    file_summary_html = FILE_SUMMARY_HEADER + "".join(file_summary_rows)

    # Test Details by File
    details_html_parts = []
    for (idx, fname, fCount, fFails, fSkipped, fTime, fTs, details) in results:
        details_html_parts.append(f'<h3 id="details_{idx}" style="text-align:left;">{idx}) {fname}</h3>')
        details_html_parts.append("""
<table class="utests" style="width:100%; table-layout: fixed;">
  <colgroup>
    <col style="width:auto;">
    <col style="width:12ch; overflow:hidden; white-space:nowrap; text-overflow:ellipsis;">
    <col style="width:9ch; overflow:hidden; white-space:nowrap; text-overflow:ellipsis;">
  </colgroup>
""")
        details_html_parts.append(generate_row(["Test name", "Duration", "Result"], is_header=True))
        for (tname, ttime, stobj) in details:
            details_html_parts.append(generate_row([tname, f"{ttime:.2f}", stobj]))
        details_html_parts.append("</table><br/>\n")
    test_details_html = "".join(details_html_parts)

    html = HTML_TEMPLATE.format(
        topTitle=top_title_html,
        overallSummary=overall_summary_html,
        fileSummary=file_summary_html,
        testDetailsByFile=test_details_html
    )

    # 파일 쓰기
    os.makedirs(os.path.dirname(outFile), exist_ok=True)
    with open(outFile, "w", encoding="utf-8") as f:
        f.write(html)

def main():
    if len(sys.argv) < 5:
        print("Usage: genHtmlReportFromGtest.py <A> <B> <output_html> <xml1> [xml2 ...]")
        sys.exit(1)
    A = sys.argv[1]; B = sys.argv[2]; out_html = sys.argv[3]
    pattern = sys.argv[4]
    xml_files = glob.glob(pattern) if '*' in pattern else [pattern] + sys.argv[5:]
    result = parse_all_files(xml_files)
    build_html(A, B, out_html, result)

    # 정적 리소스 복사
    dest = os.path.dirname(out_html) or "."
    if os.path.isdir("./html_resources"):
        for res in glob.glob("./html_resources/*"):
            shutil.copy(res, os.path.join(dest, os.path.basename(res)))

if __name__ == "__main__":
    main()
