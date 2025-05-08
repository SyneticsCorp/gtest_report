# scripts/generator.py
"""
Generates an HTML report from parsed test data and copies necessary resources.
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
<tr><th>Report name</th><th>Total unit tests</th><th>Failure</th><th>Duration</th><th>Timestamp</th></tr>
{file_summary}
</table>

<h2>Test Details by File</h2>
{test_details}

</body>
</html>"""

def format_icon(status: str) -> str:
    fn = ICON_FILES.get(status, ICON_FILES['skipped'])
    return f'<img src="html_resources/{fn}" alt="{status}" class="icon" width="16" height="16"/>'

def row_html(cells: list[str], header: bool=False) -> str:
    tag = 'th' if header else 'td'
    inner = ''.join(f'<{tag}>{c}</{tag}>' for c in cells)
    return f'<tr>{inner}</tr>\n'

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
    # earliest timestamp
    earliest = min(all_ts).strftime("%Y-%m-%dT%H:%M:%S") if all_ts else ''

    # overall summary
    overall = [
        row_html(['Total XML files',    str(len(results))]),
        row_html(['Total tests',        str(total)]),
        row_html(['Executed tests',     str(executed)]),
        row_html(['Success tests',      str(successes)]),
        row_html(['Failure tests',      str(failures)]),
        row_html(['Skipped tests',      str(skipped)]),
        row_html(['Earliest timestamp', earliest]),
    ]
    overall_summary = ''.join(overall)

    # file summary
    files_html = []
    for res in results:
        ts = res.timestamp.strftime("%Y-%m-%dT%H:%M:%S") if res.timestamp else ''
        files_html.append(row_html([
            f'<a href="#detail_{res.filename}">{res.filename}</a>',
            str(res.total),
            str(res.failures),
            f"{res.duration:.2f}",
            ts
        ]))
    file_summary = ''.join(files_html)

    # details
    details = []
    for res in results:
        details.append(f'<h3 id="detail_{res.filename}">{res.filename}</h3>\n')
        details.append("""
<table class="utests" style="width:100%; table-layout:fixed;">
 <colgroup>
   <col style="width:auto;">
   <col style="width:12ch; overflow:hidden; white-space:nowrap; text-overflow:ellipsis;">
   <col style="width:9ch;  overflow:hidden; white-space:nowrap; text-overflow:ellipsis;">
 </colgroup>
""")
        details.append(row_html(['Test name', 'Duration', 'Result'], header=True))
        for case in res.cases:
            details.append(row_html([
                case.name,
                f"{case.time:.2f}",
                format_icon(case.status)
            ]))
        details.append("</table><br/>\n")
    test_details = ''.join(details)

    # fill & write
    title = f"{project_name} {report_name} Report"
    html = HTML_TEMPLATE.format(
        title=title,
        overall_summary=overall_summary,
        file_summary=file_summary,
        test_details=test_details
    )
    out_dir = os.path.dirname(output_path) or '.'
    os.makedirs(out_dir, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    # copy resources
    dest = os.path.join(out_dir, 'html_resources')
    shutil.copytree(RESOURCES_DIR, dest, dirs_exist_ok=True)
