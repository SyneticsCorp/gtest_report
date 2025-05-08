# File: gtest_report/cli.py

"""
Command-line interface for generating multiple GTest HTML reports and an index.
사용법: gtest-report <project_name> <input_root_dir> <output_dir>
"""
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .parser import parse_files
from .generator import generate_report

# 고정 리포트 타입과 표시 이름
REPORT_TYPES = ['UT', 'UIT', 'CT', 'CIT', 'SRT']
DISPLAY_NAMES = {
    'UT': 'Unit Test',
    'UIT': 'Unit Integration Test',
    'CT': 'Component Test',
    'CIT': 'Component Integration Test',
    'SRT': 'SW Requirement Test'
}

def build_index_row(report_type: str, xml_paths: list[Path], project_name: str) -> str:
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
        return (
            f'<td>{name}</td>'
            + ''.join('<td>NT</td>' for _ in range(7))
        )

def main():
    if len(sys.argv) != 4:
        print("Usage: gtest-report <project_name> <input_root_dir> <output_dir>")
        sys.exit(1)
    project_name = sys.argv[1]
    input_root   = Path(sys.argv[2])
    output_root  = Path(sys.argv[3])
    output_root.mkdir(parents=True, exist_ok=True)

    print(f"Starting report generation for project: {project_name}")
    print(f"Input: {input_root}, Output: {output_root}\n")

    index_rows = []
    for rtype in REPORT_TYPES:
        xml_dir   = input_root / rtype
        xml_files = list(xml_dir.glob('*.xml'))
        name      = DISPLAY_NAMES[rtype]
        print(f"Processing {rtype} ({name}): {len(xml_files)} XML files found.")
        if xml_files:
            try:
                generate_report(project_name, name, xml_files, output_root / f"{rtype}_Report.html")
                print(f"  → {rtype}_Report.html generated")
            except Exception as e:
                print(f"  ERROR generating {rtype}: {e}")
        else:
            print(f"  → No XMLs for {rtype}, marking NT")
        index_rows.append(f"<tr>{build_index_row(rtype, xml_files, project_name)}</tr>")

    # index.html 렌더링
    tpl_dir = Path(__file__).parent / 'templates'
    env     = Environment(
        loader=FileSystemLoader(str(tpl_dir)),
        autoescape=select_autoescape(['html'])
    )
    tpl     = env.get_template('index.html')
    content = tpl.render(
        project_name=project_name,
        index_rows=index_rows
    )
    (output_root / 'index.html').write_text(content, encoding='utf-8')

    print(f"\nIndex generated at {output_root/'index.html'}")
    print("All reports processed successfully.")

if __name__ == '__main__':
    main()
