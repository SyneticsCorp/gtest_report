# File: gtest_report/generator.py

"""
Generates an HTML report with two Chart.js pie charts:
- Execution Rate (Executed vs Skipped)
- Success Rate (Success vs Failure)
Also populates Overall Summary with Execution Rate and Success Rate,
and restores clickable links in the Failed Tests table.
Requires: pip install jinja2
"""
import json
from pathlib import Path
from datetime import datetime
import shutil

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .parser import parse_files

RESOURCES_DIR = Path(__file__).parent / 'html_resources'
ICON_FILES    = {
    'success': 'gtest_report_ok.png',
    'failed':  'gtest_report_notok.png',
    'skipped': 'gtest_report_disable.png'
}

def format_icon(status: str) -> str:
    fn = ICON_FILES.get(status, ICON_FILES['skipped'])
    return f'<img src="html_resources/{fn}" alt="{status}" class="icon" width="16" height="16"/>'

def row_html(cells: list[str], header: bool=False) -> str:
    tag = 'th' if header else 'td'
    return ''.join(f'<{tag}>{c}</{tag}>' for c in cells)

def split_test_name(full: str) -> tuple[str,str]:
    parts = full.split('.',1)
    return (parts[0], parts[1]) if len(parts)==2 else ('', full)

def sanitize_id(text: str) -> str:
    # 안전한 HTML id 생성
    return ''.join(c if c.isalnum() or c=='_' else '_' for c in text)

def generate_report(
    project_name: str,
    report_name: str,
    xml_paths: list[Path],
    output_path: Path
):
    # 1) XML 파싱
    results, total, failures, skipped, timestamps = parse_files(xml_paths)
    executed  = total - skipped
    successes = executed - failures
    earliest  = min(timestamps).strftime("%Y-%m-%d %H:%M:%S") if timestamps else ''

    # 2) 리소스 복사
    out_dir = output_path.parent
    (out_dir / 'html_resources').mkdir(exist_ok=True)
    shutil.copytree(RESOURCES_DIR, out_dir / 'html_resources', dirs_exist_ok=True)

    # 3) Overall Summary 테이블 행 (Execution & Success rate 추가)
    overall_rows = [
        row_html(['Total XML files',    str(len(results))]),
        row_html(['Total tests',        str(total)]),
        row_html(['Executed tests',     str(executed)]),
        row_html(['Execution rate',     f"{executed/total*100:.2f}%"]),
        row_html(['Success tests',      str(successes)]),
        row_html(['Success rate',       f"{successes/total*100:.2f}%"]),
        row_html(['Failure tests',      f'<span style="color:red;">{failures}</span>']),
        row_html(['Skipped tests',      str(skipped)]),
        row_html(['Earliest timestamp', earliest])
    ]

    # 4) Failed Tests 테이블 행 (Test Case에 링크 복원)
    failed_rows = [row_html(['Test Suite','Test Case','Result'], header=True)]
    for res in results:
        for case in res.cases:
            if case.status == 'failed':
                suite, case_name = split_test_name(case.name)
                # 고유 ID 생성
                test_id = sanitize_id(f"{res.filename}_{case.name}")
                link    = f'<a href="#test_{test_id}">{case_name}</a>'
                failed_rows.append(
                    row_html([suite, link, format_icon(case.status)])
                )

    # 5) File Summary 테이블 행
    file_rows = [row_html(['Report Name','Total','Failure','Timestamp'], header=True)]
    for res in results:
        ts = res.timestamp.strftime("%Y-%m-%d %H:%M:%S") if res.timestamp else ''
        fh = f'<span style="color:red;">{res.failures}</span>' if res.failures else '0'
        file_rows.append(
            row_html([
                f'<a href="#detail_{res.filename}">{res.filename}</a>',
                str(res.total), fh, ts
            ])
        )

    # 6) Test Details by File
    detail_parts = []
    for res in results:
        detail_parts.append(f'<h3 id="detail_{res.filename}">{res.filename}</h3>')
        detail_parts.append("""
<table class="utests">
  <colgroup>
    <col style="width:40%;">
    <col style="width:40%;">
    <col style="width:20%;">
  </colgroup>
""")
        detail_parts.append(row_html(['Test Suite','Test Case','Result'], header=True))
        for case in res.cases:
            suite, case_name = split_test_name(case.name)
            row_id = sanitize_id(f"{res.filename}_{case.name}")
            detail_parts.append(
                f'<tr id="test_{row_id}">'
                + row_html([suite, case_name, format_icon(case.status)])
                + '</tr>'
            )
        detail_parts.append('</table><br/>')

    # 7) 차트용 데이터 JSON 직렬화
    exec_labels = json.dumps(['Executed','Skipped'])
    exec_values = json.dumps([executed, skipped])
    succ_labels = json.dumps(['Success','Failure'])
    succ_values = json.dumps([successes, failures])

    # 8) Jinja2 렌더링
    tpl_dir = Path(__file__).parent / 'templates'
    env     = Environment(
        loader=FileSystemLoader(str(tpl_dir)),
        autoescape=select_autoescape(['html'])
    )
    tpl  = env.get_template('report.html')
    html = tpl.render(
        title        = f"{project_name} {report_name}",
        overall_rows = overall_rows,
        failed_rows  = failed_rows,
        file_rows    = file_rows,
        test_details = detail_parts,
        exec_labels  = exec_labels,
        exec_values  = exec_values,
        succ_labels  = succ_labels,
        succ_values  = succ_values
    )
    output_path.write_text(html, encoding='utf-8')
