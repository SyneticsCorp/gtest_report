# File: scripts/generator.py
"""
Generates an HTML report from parsed test data and copies necessary resources.
(Includes execution and success rate bar chart under Overall Summary using matplotlib.)
Requires matplotlib: install via `pip install matplotlib`
"""
import os
import shutil
from parser import parse_files
from datetime import datetime
import matplotlib.pyplot as plt

# resources under scripts/html_resources/
RESOURCES_DIR = os.path.join(os.path.dirname(__file__), 'html_resources')
ICON_FILES = {
    'success': 'gtest_report_ok.png',
    'failed':  'gtest_report_notok.png',
    'skipped': 'gtest_report_disable.png'
}

HTML_TEMPLATE = '''<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>{title} Report</title>
  <link rel="stylesheet" href="html_resources/gtest_report.css">
  <script src="html_resources/extraScript.js"></script>
</head>
<body>
<h1>{title} Report</h1>

<h2>Overall Summary</h2>
<table class="overall_summary">
{overall_summary}
</table>

<!-- Bar Chart -->
<div class="charts" style="text-align:center; margin:1rem 0;">
  <img src="html_resources/rate_bar.png" alt="Execution and Success Rates">
</div>

<h2>Failed Tests</h2>
{failed_section}

<h2>File Summary</h2>
<table class="file_summary">
<tr><th>Report name</th><th>Total tests</th><th>Failure</th><th>Timestamp</th></tr>
{file_summary}
</table>

<h2>Test Details by File</h2>
{test_details}

</body>
</html>'''


def format_icon(status: str) -> str:
    fn = ICON_FILES.get(status, ICON_FILES['skipped'])
    return f'<img src="html_resources/{fn}" alt="{status}" class="icon" width="16" height="16"/>'


def row_html(cells: list[str], header: bool=False) -> str:
    tag = 'th' if header else 'td'
    inner = ''.join(f'<{tag}>{c}</{tag}>' for c in cells)
    return f'<tr>{inner}</tr>\n'


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

    # bar chart
    labels = ['Executed', 'Success']
    values = [executed/total*100 if total else 0, successes/total*100 if total else 0]
    fig, ax = plt.subplots(figsize=(4,1.5))
    ax.barh(labels, values)
    ax.set_xlim(0,100)
    ax.set_xlabel('Percentage')
    for i, v in enumerate(values):
        ax.text(v + 1, i, f"{v:.1f}%", va='center')
    plt.tight_layout()
    plt.savefig(os.path.join(res_dir, 'rate_bar.png'), bbox_inches='tight')
    plt.close()

    # summary percentages
    exec_pct    = f"{executed/total*100:.2f}%" if total else "0.00%"
    success_pct = f"{successes/total*100:.2f}%" if total else "0.00%"

    # build overall summary rows
    overall_rows = [
        row_html(['Total XML files',    str(len(results))]),
        row_html(['Total tests',        str(total)]),
        row_html(['Executed tests',     str(executed)]),
        row_html(['Execution rate',     exec_pct]),
        row_html(['Success tests',      str(successes)]),
        row_html(['Success rate',       success_pct]),
        row_html(['Failure tests',      f'<span style="color:red;">{failures}</span>']),
        row_html(['Skipped tests',      str(skipped)]),
        row_html(['Earliest timestamp', earliest])
    ]
    overall_summary = ''.join(overall_rows)

    # build failed section
    failed_rows = [row_html(['Report Name', 'Test Name'], header=True)]
    for res in results:
        for case in res.cases:
            if case.status == 'failed':
                test_id = sanitize_id(f"{res.filename}_{case.name}")
                link = f'<a href="#test_{test_id}">{case.name}</a>'
                failed_rows.append(row_html([res.filename, link]))
    if len(failed_rows) > 1:
        failed_section = (
            '<table class="failed_tests">\n'
            + ''.join(failed_rows)
            + '</table>\n'
        )
    else:
        failed_section = '<div>No failed tests</div>\n'

    # file summary rows
    file_rows = []
    for res in results:
        ts = res.timestamp.strftime("%Y-%m-%d %H:%M:%S") if res.timestamp else ''
        fail_html = f'<span style="color:red;">{res.failures}</span>' if res.failures>0 else str(res.failures)
        file_rows.append(row_html([
            f'<a href="#detail_{res.filename}">{res.filename}</a>',
            str(res.total),
            fail_html,
            ts
        ]))
    file_summary = ''.join(file_rows)

    # test details by file with split suite/case
    detail_parts = []
    for res in results:
        detail_parts.append(f'<h3 id="detail_{res.filename}">{res.filename}</h3>\n')
        detail_parts.append(
"""
<table class="utests" style="width:100%; table-layout:fixed;">
 <colgroup>
   <col style="width:40%;">
   <col style="width:40%;">
   <col style="width:20%;">
 </colgroup>
"""
        )
        detail_parts.append(row_html(['Test Suite', 'Test Case', 'Result'], header=True))
        for case in res.cases:
            suite, case_name = split_test_name(case.name)
            row_id = f'test_{sanitize_id(res.filename)}_{sanitize_id(case.name)}'
            detail_parts.append(
                f'<tr id="{row_id}">'
                f'<td>{suite}</td>'
                f'<td>{case_name}</td>'
                f'<td>{format_icon(case.status)}</td>'
                '</tr>\n'
            )
        detail_parts.append('</table><br/>\n')
    test_details = ''.join(detail_parts)

    # write output
    title = f"{project_name} {report_name}"
    html = HTML_TEMPLATE.format(
        title=title,
        overall_summary=overall_summary,
        failed_section=failed_section,
        file_summary=file_summary,
        test_details=test_details
    )
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
