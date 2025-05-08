# File: scripts/cli.py
"""
Command-line interface for generating multiple GTest HTML reports and an index.
- Accepts project name, input root directory, and output directory
- Scans input root for subfolders UT, UIT, CT, CIT, SRT
- Logs detailed processing info: number of XMLs found, processed, and error details
- Generates individual reports {TYPE}_Report.html in output directory
  with title "<project_name> <Test Type> Report"
- Creates index.html titled "<project_name> Test Report" summarizing each report
- Report types with no tests display NT for all values and link
- Adds footnote: NT: Not Tested
- Maps abbreviations to full names and adjusts column widths
Version: 1
"""
import os
import glob
import sys
from datetime import datetime

from jinja2 import Environment, FileSystemLoader

from parser import parse_files
from generator import generate_report

# Fixed report types and display names
REPORT_TYPES = ['UT', 'UIT', 'CT', 'CIT', 'SRT']
DISPLAY_NAMES = {
    'UT': 'Unit Test',
    'UIT': 'Unit Integration Test',
    'CT': 'Component Test',
    'CIT': 'Component Integration Test',
    'SRT': 'SW Requirement Test'
}

def build_index_row(report_type, xml_paths, project_name):
    name = DISPLAY_NAMES.get(report_type, report_type)
    if xml_paths:
        results, total, failures, skipped, timestamps = parse_files(xml_paths)
        executed  = total - skipped
        successes = executed - failures
        timestamp = min(timestamps).strftime("%Y-%m-%d %H:%M:%S") if timestamps else ''
        link = f'<a href="{report_type}_Report.html">View</a>'
        fail_html = f'<span style="color:red;">{failures}</span>' if failures > 0 else '0'
        return (
            f'<td>{name}</td>'
            f'<td>{total}</td>'
            f'<td>{executed}</td>'
            f'<td>{successes}</td>'
            f'<td>{fail_html}</td>'
            f'<td>{skipped}</td>'
            f'<td>{timestamp}</td>'
            f'<td>{link}</td>'
        )
    else:
        # No tests: display NT
        return (
            f'<td>{name}</td>'
            f'<td>NT</td>'
            f'<td>NT</td>'
            f'<td>NT</td>'
            f'<td>NT</td>'
            f'<td>NT</td>'
            f'<td>NT</td>'
            f'<td>NT</td>'
        )

def main():
    if len(sys.argv) != 4:
        print("Usage: cli.py <project_name> <input_root_dir> <output_dir>")
        sys.exit(1)
    project_name = sys.argv[1]
    input_root   = sys.argv[2]
    output_root  = sys.argv[3]
    os.makedirs(output_root, exist_ok=True)

    print(f"Starting report generation for project: {project_name}")
    print(f"Input root: {input_root}")
    print(f"Output root: {output_root}\n")

    index_rows = []
    for rtype in REPORT_TYPES:
        name      = DISPLAY_NAMES.get(rtype)
        xml_dir   = os.path.join(input_root, rtype)
        xml_files = glob.glob(os.path.join(xml_dir, '*.xml'))
        count     = len(xml_files)
        print(f"Processing {rtype} ({name}): found {count} XML files.")
        if xml_files:
            try:
                report_title = DISPLAY_NAMES.get(rtype, rtype)
                out_file     = os.path.join(output_root, f"{rtype}_Report.html")
                generate_report(project_name, report_title, xml_files, out_file)
                print(f"  -> Generated {rtype}_Report.html")
            except Exception as e:
                print(f"  ERROR generating report for {rtype}: {e}")
        else:
            print(f"  -> No XML files for {rtype}, marked NT.")
        # build <tr> inner HTML
        row_inner = build_index_row(rtype, xml_files, project_name)
        index_rows.append(f"<tr>{row_inner}</tr>\n")

    # render index.html from template
    tpl_dir = os.path.join(os.path.dirname(__file__), 'templates')
    env     = Environment(loader=FileSystemLoader(tpl_dir))
    tpl     = env.get_template('index.html')
    html    = tpl.render(
        project_name=project_name,
        index_rows=index_rows
    )
    index_path = os.path.join(output_root, 'index.html')
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"\nIndex generated at {index_path}")
    print("All reports processed successfully.")

if __name__ == '__main__':
    main()
