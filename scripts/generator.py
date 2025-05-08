# File: scripts/generator.py
"""
Generates an HTML report from parsed test data and copies necessary resources.
"""
import os
import shutil
from datetime import datetime
from parser import parse_files

# Resources directory under scripts/html_resources
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
  <title>{title}</title>
  <link rel="stylesheet" href="html_resources/gtest_report.css">
  <script src="html_resources/extraScript.js"></script>
</head>
<body>
<h1>{title}</h1>

<h2>Overall Summary</h2>
<table class="overall_summary">
{overall_summary}
</table>

<h2>File Summary</h2>
<table class="file_summary">
<tr><th>Report name</th><th>Total</th><th>Fail</th><th>Skipped</th><th>Duration</th><th>Timestamp</th></tr>
{file_summary}
</table>

<h2>Test Details by File</h2>
{test_details}

</body>
</html>'''

def format_icon(status: str) -> str:
    """
    Return an <img> tag for the given status.
    """
    icon_file = ICON_FILES.get(status, ICON_FILES['skipped'])
    return (
        f'<img src="html_resources/{icon_file}" '
        f'alt="{status}" class="icon" width="16" height="16"/>'
    )

def row_html(cells: list[str], header: bool = False) -> str:
    """
    Generate a single table row, using <th> for headers or <td> for data.
    """
    tag = 'th' if header else 'td'
    parts = []
    for c in cells:
        parts.append(f'<{tag}>{c}</{tag}>')
    return '<tr>' + ''.join(parts) + '</tr>\n'

def generate_report(
    project_name: str,
    report_name: str,
    xml_paths: list[str],
    output_path: str
) -> None:
    # 1) Parse XML files
    results, total, failures, skipped, timestamps = parse_files(xml_paths)
    executed   = total - skipped
    successes  = executed - failures
    earliest_ts = min(timestamps).isoformat() if timestamps else ''

    # 2) Build Overall Summary
    overall_rows = [
        row_html(['Total XML files',    str(len(results))]),
        row_html(['Total tests',        str(total)]),
        row_html(['Executed tests',     str(executed)]),
        row_html(['Success tests',      str(successes)]),
        row_html(['Failure tests',      str(failures)]),
        row_html(['Skipped tests',      str(skipped)]),
        row_html(['Earliest timestamp', earliest_ts]),
    ]
    overall_summary = ''.join(overall_rows)

    # 3) Build File Summary
    file_rows = []
    for res in results:
        ts_str = res.timestamp.isoformat() if res.timestamp else ''
        file_rows.append(row_html([
            f'<a href="#detail_{res.filename}">{res.filename}</a>',
            str(res.total),
            str(res.failures),
            str(res.skipped),
            f"{res.duration:.2f}",
            ts_str
        ]))
    file_summary = ''.join(file_rows)

    # 4) Build Test Details by File (with original colgroup)
    detail_parts = []
    for res in results:
        detail_parts.append(f'<h3 id="detail_{res.filename}">{res.filename}</h3>\n')
        detail_parts.append("""
<table class="utests" style="width:100%; table-layout:fixed;">
 <colgroup>
   <col style="width:auto;">
   <col style="width:12ch; overflow:hidden; white-space:nowrap; text-overflow:ellipsis;">
   <col style="width:9ch;  overflow:hidden; white-space:nowrap; text-overflow:ellipsis;">
 </colgroup>
""")
        # Header
        detail_parts.append(row_html(['Test name', 'Duration', 'Result'], header=True))
        # Data rows
        for case in res.cases:
            detail_parts.append(row_html([
                case.name,
                f"{case.time:.2f}",
                format_icon(case.status)
            ]))
        detail_parts.append("</table><br/>\n")
    test_details = ''.join(detail_parts)

    # 5) Fill HTML template
    title = f"{project_name} {report_name} Report"
    html_content = HTML_TEMPLATE.format(
        title=title,
        overall_summary=overall_summary,
        file_summary=file_summary,
        test_details=test_details
    )

    # 6) Write HTML output
    out_dir = os.path.dirname(output_path) or '.'
    os.makedirs(out_dir, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    # 7) Copy resources (CSS/JS/Icons)
    dest_res = os.path.join(out_dir, 'html_resources')
    shutil.copytree(RESOURCES_DIR, dest_res, dirs_exist_ok=True)
