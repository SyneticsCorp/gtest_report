# File: scripts/generator.py
"""
Generates an HTML report from parsed test data and copies necessary resources.
(Includes execution and success rate bar chart under Overall Summary using matplotlib.)
Requires: pip install matplotlib jinja2
"""
import os
import shutil
from datetime import datetime

import matplotlib.pyplot as plt
from jinja2 import Environment, FileSystemLoader

from parser import parse_files

# resources under scripts/html_resources/
RESOURCES_DIR = os.path.join(os.path.dirname(__file__), 'html_resources')
ICON_FILES    = {
    'success': 'gtest_report_ok.png',
    'failed':  'gtest_report_notok.png',
    'skipped': 'gtest_report_disable.png'
}

def format_icon(status: str) -> str:
    fn = ICON_FILES.get(status, ICON_FILES['skipped'])
    return f'<img src="html_resources/{fn}" alt="{status}" class="icon" width="16" height="16"/>'

def row_html(cells: list[str], header: bool=False) -> str:
    tag   = 'th' if header else 'td'
    inner = ''.join(f'<{tag}>{c}</{tag}>' for c in cells)
    return inner  # safe to embed into <tr> in template

def sanitize_id(text: str) -> str:
    return ''.join(c if c.isalnum() or c=='_' else '_' for c in text)

def split_test_name(full_name: str) -> tuple[str,str]:
    parts = full_name.split('.', 1)
    if len(parts) == 2:
        return parts[0], parts[1]
    return '', full_name

def generate_report(
    project_name: str,
    report_name: str,
    xml_paths: list[str],
    output_path: str
):
    # parse
    results, total, failures, skipped, all_ts = parse_files(xml_paths)
    executed  = total - skipped
    successes = executed - failures
    earliest  = min(all_ts).strftime("%Y-%m-%d %H:%M:%S") if all_ts else ''

    # prepare resources
    out_dir = os.path.dirname(output_path) or '.'
    res_dir = os.path.join(out_dir, 'html_resources')
    os.makedirs(res_dir, exist_ok=True)
    shutil.copytree(RESOURCES_DIR, res_dir, dirs_exist_ok=True)

    # generate bar chart
    labels = ['Executed', 'Success']
    values = [
        executed/total*100 if total else 0,
        successes/total*100 if total else 0
    ]
    fig, ax = plt.subplots(figsize=(4, 1.5))
    ax.barh(labels, values)
    ax.set_xlim(0, 100)
    for i, v in enumerate(values):
        ax.text(v + 1, i, f"{v:.1f}%", va='center')
    plt.tight_layout()
    plt.savefig(os.path.join(res_dir, 'rate_bar.png'), bbox_inches='tight')
    plt.close()

    # build table rows
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

    failed_rows = [row_html(['Report Name', 'Test Name'], header=True)]
    for res in results:
        for case in res.cases:
            if case.status == 'failed':
                test_id = sanitize_id(f"{res.filename}_{case.name}")
                link    = f'<a href="#test_{test_id}">{case.name}</a>'
                failed_rows.append(row_html([res.filename, link]))

    file_rows = []
    for res in results:
        ts        = res.timestamp.strftime("%Y-%m-%d %H:%M:%S") if res.timestamp else ''
        fail_html = f'<span style="color:red;">{res.failures}</span>' if res.failures > 0 else '0'
        file_rows.append(row_html([
            f'<a href="#detail_{res.filename}">{res.filename}</a>',
            str(res.total),
            fail_html,
            ts
        ]))

    detail_parts = []
    for res in results:
        detail_parts.append(f'<h3 id="detail_{res.filename}">{res.filename}</h3>')
        detail_parts.append("""
<table class="utests" style="width:100%; table-layout:fixed;">
 <colgroup>
   <col style="width:40%;">
   <col style="width:40%;">
   <col style="width:20%;">
 </colgroup>
""")
        detail_parts.append(row_html(['Test Suite', 'Test Case', 'Result'], header=True))
        for case in res.cases:
            suite, case_name = split_test_name(case.name)
            row_id = f'test_{sanitize_id(res.filename)}_{sanitize_id(case.name)}'
            detail_parts.append(
                f'<tr id="{row_id}">'
                f'<td>{suite}</td>'
                f'<td>{case_name}</td>'
                f'<td>{format_icon(case.status)}</td>'
                '</tr>'
            )
        detail_parts.append('</table><br/>')

    # render from Jinja2 template
    tpl_dir = os.path.join(os.path.dirname(__file__), 'templates')
    env     = Environment(loader=FileSystemLoader(tpl_dir))
    tpl     = env.get_template('report.html')
    html    = tpl.render(
        title=f"{project_name} {report_name}",
        overall_rows=overall_rows,
        failed_rows=failed_rows,
        file_rows=file_rows,
        test_details=detail_parts
    )
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
