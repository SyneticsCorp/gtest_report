# File: scripts/cli.py
"""
Command-line interface for generating multiple GTest HTML reports and an index.
- Accepts a project name, input root directory, and output directory
- Scans input root for subfolders UT, UIT, CT, CIT, SRT
- Generates individual reports {folder}_Report.html in output directory
  with title: <project_name> <Test Type> Report
- Creates index.html titled "<project_name> Test Report" summarizing each report
- Report types with no tests display NT for all values and link
- Adds footnote: NT: Not Tested
Version: 1
"""
import os
import glob
import sys
from generator import generate_report
from parser import parse_files
from datetime import datetime

# Fixed report types and display names
REPORT_TYPES = ['UT', 'UIT', 'CT', 'CIT', 'SRT']
DISPLAY_NAMES = {
    'UT': 'Unit Test',
    'UIT': 'Unit Integration Test',
    'CT': 'Component Test',
    'CIT': 'Component Integration Test',
    'SRT': 'SW Requirement Test'
}

# Index HTML template with column width adjustments
INDEX_TEMPLATE = '''<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>{project_name} Test Report</title>
  <link rel="stylesheet" href="html_resources/gtest_report.css">
</head>
<body>
<h1>{project_name} Test Report</h1>
<table class="index_summary">
<colgroup>
  <col style="width:20%">
  <col style="width:10%">
  <col style="width:10%">
  <col style="width:10%">
  <col style="width:10%">
  <col style="width:10%">
  <col style="width:20%">
  <col style="width:10%">
</colgroup>
<tr>
  <th>Report Type</th>
  <th>Total Tests</th>
  <th>Executed</th>
  <th>Success</th>
  <th>Failure</th>
  <th>Skipped</th>
  <th>Timestamp</th>
  <th>Link</th>
</tr>
{rows}
</table>
<div style="margin-top:0.5rem;font-size:0.9em;">NT: Not Tested</div>
</body>
</html>'''


def build_index_row(report_type, xml_paths, project_name):
    # Display full name
    name = DISPLAY_NAMES.get(report_type, report_type)
    if xml_paths:
        results, total, failures, skipped, timestamps = parse_files(xml_paths)
        executed  = total - skipped
        successes = executed - failures
        timestamp = min(timestamps).strftime("%Y-%m-%d %H:%M:%S") if timestamps else ''
        link = f'<a href="{report_type}_Report.html">View</a>'
        fail_html = f'<span style="color:red;">{failures}</span>' if failures > 0 else str(failures)
        return (
            f'<tr>'
            f'<td>{name}</td>'
            f'<td>{total}</td>'
            f'<td>{executed}</td>'
            f'<td>{successes}</td>'
            f'<td>{fail_html}</td>'
            f'<td>{skipped}</td>'
            f'<td>{timestamp}</td>'
            f'<td>{link}</td>'
            '</tr>\n'
        )
    else:
        # No tests: display NT
        return (
            f'<tr>'
            f'<td>{name}</td>'
            f'<td>NT</td>'
            f'<td>NT</td>'
            f'<td>NT</td>'
            f'<td>NT</td>'
            f'<td>NT</td>'
            f'<td>NT</td>'
            f'<td>NT</td>'
            '</tr>\n'
        )


def main():
    if len(sys.argv) != 4:
        print("Usage: cli.py <project_name> <input_root_dir> <output_dir>")
        sys.exit(1)
    project_name = sys.argv[1]
    input_root   = sys.argv[2]
    output_root  = sys.argv[3]
    os.makedirs(output_root, exist_ok=True)

    index_rows = []
    for rtype in REPORT_TYPES:
        xml_dir   = os.path.join(input_root, rtype)
        pattern   = os.path.join(xml_dir, '*.xml')
        xml_files = glob.glob(pattern)
        if xml_files:
            # Generate individual report with full name in title
            report_title = DISPLAY_NAMES.get(rtype, rtype)
            out_file     = os.path.join(output_root, f"{rtype}_Report.html")
            generate_report(project_name, report_title, xml_files, out_file)
        # Build index row regardless
        row = build_index_row(rtype, xml_files, project_name)
        index_rows.append(row)

    # Write index.html
    index_content = INDEX_TEMPLATE.format(project_name=project_name, rows=''.join(index_rows))
    index_path    = os.path.join(output_root, 'index.html')
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(index_content)
    print(f"Index generated at {index_path}")


if __name__ == '__main__':
    main()
