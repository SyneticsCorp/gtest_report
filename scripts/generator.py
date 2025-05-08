# File: scripts/generator.py
"""
Generates an HTML report from parsed test data and copies necessary resources.
(Includes a table of failed tests with Test Name links, File Summary with working Report Name links,
and highlights failure counts in red where appropriate.)
"""
import os
import shutil
from parser import parse_files
from datetime import datetime

# resources under scripts/html_resources/
RESOURCES_DIR = os.path.join(os.path.dirname(__file__), 'html_resources')
ICON_FILES = {
    'success': 'gtest_report_ok.png',
    'failed':  'gtest_report_notok.png',
    'skipped': 'gtest_report_disable.png'
}

HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
  <meta charset=\"UTF-8\">
  <title>{title}</title>
  <link rel=\"stylesheet\" href=\"html_resources/gtest_report.css\">
  <script src=\"html_resources/extraScript.js\"></script>
</head>
<body>
<h1>{title}</h1>

<h2>Overall Summary</h2>
<table class=\"overall_summary\">
{overall_summary}
</table>

<h2>Failed Tests</h2>
<table class=\"failed_tests\">
{failed_table}
</table>

<h2>File Summary</h2>
<table class=\"file_summary\">
<tr><th>Report name</th><th>Total unit tests</th><th>Failure</th><th>Timestamp</th></tr>
{file_summary}
</table>

<h2>Test Details by File</h2>
{test_details}

</body>
</html>"""

def format_icon(status: str) -> str:
    fn = ICON_FILES.get(status, ICON_FILES['skipped'])
    return f'<img src=\"html_resources/{fn}\" alt=\"{status}\" class=\"icon\" width=\"16\" height=\"16\"/>'


def row_html(cells: list[str], header: bool=False) -> str:
    tag = 'th' if header else 'td'
    inner = ''.join(f'<{tag}>{c}</{tag}>' for c in cells)
    return f'<tr>{inner}</tr>\n'


def sanitize_id(text: str) -> str:
    return ''.join(c if c.isalnum() or c=='_' else '_' for c in text)


def generate_report(
    project_name: str,
    report_name: str,
    xml_paths: list[str],
    output_path: str
):
    # parse
    results, total, failures, skipped, all_ts = parse_files(xml_paths)
    executed = total - skipped
    successes = executed - failures
    earliest = min(all_ts).strftime("%Y-%m-%dT%H:%M:%S") if all_ts else ''

    # Overall Summary
    overall_rows = [
        row_html(['Total XML files', str(len(results))]),
        row_html(['Total tests', str(total)]),
        row_html(['Executed tests', str(executed)]),
        row_html(['Success tests', str(successes)]),
        # Failure tests count in red
        row_html(['Failure tests', f'<span style=\"color:red;\">{failures}</span>']),
        row_html(['Skipped tests', str(skipped)]),
        row_html(['Earliest timestamp', earliest])
    ]
    overall_summary = ''.join(overall_rows)

    # Failed Tests Table
    failed_rows = [row_html(['Report Name', 'Test Name'], header=True)]
    for res in results:
        for case in res.cases:
            if case.status == 'failed':
                test_id = sanitize_id(f"{res.filename}_{case.name}")
                tst_link = f'<a href=\"#test_{test_id}\">{case.name}</a>'
                failed_rows.append(row_html([res.filename, tst_link]))
    failed_table = ''.join(failed_rows)

    # File Summary with conditional red styling for failures
    file_rows = []
    for res in results:
        ts = res.timestamp.strftime("%Y-%m-%dT%H:%M:%S") if res.timestamp else ''
        # style failure count red if >0
        fail_html = (
            f'<span style=\"color:red;\">{res.failures}</span>'
            if res.failures > 0 else str(res.failures)
        )
        file_rows.append(row_html([
            f'<a href=\"#detail_{res.filename}\">{res.filename}</a>',
            str(res.total),
            fail_html,
            ts
        ]))
    file_summary = ''.join(file_rows)

    # Test Details by File
    detail_parts = []
    for res in results:
        detail_parts.append(f'<h3 id=\"detail_{res.filename}\">{res.filename}</h3>\n')
        detail_parts.append(
"""
<table class=\"utests\" style=\"width:100%; table-layout:fixed;\">
 <colgroup>
   <col style=\"width:auto;\">\n
   <col style=\"width:9ch; overflow:hidden; white-space:nowrap; text-overflow:ellipsis;\">\n
 </colgroup>\n"""
        )
        detail_parts.append(row_html(['Test name', 'Result'], header=True))
        for case in res.cases:
            row_id = f'test_{sanitize_id(res.filename)}_{sanitize_id(case.name)}'
            detail_parts.append(
                f'<tr id=\"{row_id}\">'
                f'<td>{case.name}</td>'
                f'<td>{format_icon(case.status)}</td>'
                '</tr>\n'
            )
        detail_parts.append('</table><br/>\n')
    test_details = ''.join(detail_parts)

    # write HTML
    title = f"{project_name} {report_name} Report"
    html_content = HTML_TEMPLATE.format(
        title=title,
        overall_summary=overall_summary,
        failed_table=failed_table,
        file_summary=file_summary,
        test_details=test_details
    )
    out_dir = os.path.dirname(output_path) or '.'
    os.makedirs(out_dir, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    # copy resources
    shutil.copytree(RESOURCES_DIR, os.path.join(out_dir, 'html_resources'), dirs_exist_ok=True)
