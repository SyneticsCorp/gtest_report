# File: gtest_report/cli.py

"""
Command-line interface for parallel GTest HTML report generation and an index.
- Parallelizes per-test-type report generation using ProcessPoolExecutor.
- Accepts project name, input root directory, and output directory
- Logs count of XML files per type
Version: 1
"""
import sys
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .parser import parse_files
from .generator import generate_report

REPORT_TYPES = ['UT', 'UIT', 'CT', 'CIT', 'SRT']
DISPLAY_NAMES = {
    'UT':  'Unit Test',
    'UIT': 'Unit Integration Test',
    'CT':  'Component Test',
    'CIT': 'Component Integration Test',
    'SRT': 'SW Requirement Test',
}

def build_index_cells(report_type: str, xml_paths: list[Path]) -> str:
    """Generate <td>…</td> cells for the index row of a given type."""
    name = DISPLAY_NAMES[report_type]
    if xml_paths:
        results, total, failures, skipped, timestamps = parse_files(xml_paths)
        executed  = total - skipped
        successes = executed - failures
        ts_str    = min(timestamps).strftime("%Y-%m-%d %H:%M:%S") if timestamps else ''
        link      = f'<a href="{report_type}_Report.html">View</a>'
        fail_html = f'<span style="color:red;">{failures}</span>' if failures > 0 else '0'
        cells = [name, str(total), str(executed), str(successes),
                 fail_html, str(skipped), ts_str, link]
    else:
        cells = [name] + ['NT'] * 7

    return ''.join(f'<td>{c}</td>' for c in cells)

def _worker(task):
    """Worker function for parallel report generation."""
    rtype, project, report_name, xmls, out_root = task
    try:
        generate_report(project, report_name, xmls, out_root / f"{rtype}_Report.html")
        return (rtype, True, None)
    except Exception as e:
        return (rtype, False, str(e))

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

    tasks = []
    # Log XML count and prepare tasks
    for rtype in REPORT_TYPES:
        xml_dir = input_root / rtype
        xmls    = list(xml_dir.glob("*.xml"))
        count   = len(xmls)
        name    = DISPLAY_NAMES[rtype]
        print(f"Processing {rtype} ({name}): {count} XML files found.")
        tasks.append((rtype, project_name, name, xmls, output_root))

    # Parallel execution
    with ProcessPoolExecutor() as executor:
        future_map = {executor.submit(_worker, t): t[0] for t in tasks}
        for future in as_completed(future_map):
            rtype, success, err = future.result()
            if success:
                print(f"  → {rtype}_Report.html generated")
            else:
                print(f"[ERROR] Generating {rtype}: {err}", file=sys.stderr)

    # Build index rows
    index_rows = [
        build_index_cells(rtype, list((input_root / rtype).glob("*.xml")))
        for rtype in REPORT_TYPES
    ]

    # Render index.html
    tpl_dir = Path(__file__).parent / "templates"
    env     = Environment(
        loader=FileSystemLoader(str(tpl_dir)),
        autoescape=select_autoescape(["html"])
    )
    tpl     = env.get_template("index.html")
    content = tpl.render(project_name=project_name, index_rows=index_rows)
    (output_root / "index.html").write_text(content, encoding="utf-8")

    print(f"\nIndex generated at {output_root/'index.html'}")
    print("All reports processed successfully.")

if __name__ == "__main__":
    main()
