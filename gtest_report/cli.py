"""
CLI entry point:
- Parallel generation of UT/UIT/CT/CIT/SRT reports
- Renders index.html with:
    * Jenkins build info
    * Overall Results
      - Summary by Test Stage
      - Test Coverage
"""
import sys
import argparse
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime

from .parser import parse_files
from .builder.html_builder import render_report
from jinja2 import Environment, FileSystemLoader, select_autoescape

REPORT_TYPES  = ["UT", "UIT", "CT", "CIT", "SRT"]
DISPLAY_NAMES = {
    "UT":  "Unit Test",
    "UIT": "Unit Integration Test",
    "CT":  "Component Test",
    "CIT": "Component Integration Test",
    "SRT": "SW Requirement Test",
}


def build_index_cells(report_type: str, xml_paths: list[Path]) -> str:
    """Generate <td>…</td> cells for the Summary by Test Stage table."""
    name = DISPLAY_NAMES[report_type]
    if xml_paths:
        results, total, failures, skipped, timestamps = parse_files(xml_paths)
        executed = total - skipped
        successes = executed - failures
        # split skipped
        skipped_with_reason = 0
        skipped_no_reason   = 0
        for fr in results:
            for case in fr.cases:
                if case.status == "skipped":
                    if getattr(case, "failure_message", "").strip():
                        skipped_with_reason += 1
                    else:
                        skipped_no_reason += 1
        ts_str    = min(timestamps).strftime("%Y-%m-%d %H:%M:%S") if timestamps else ""
        link      = f'<a href="{report_type}_Report.html">View</a>'
        fail_html = f'<span style="color:red;">{failures}</span>' if failures else "0"
        cells = [
            name,
            str(total),
            str(executed),
            str(successes),
            fail_html,
            str(skipped_no_reason),
            str(skipped_with_reason),
            ts_str,
            link,
        ]
    else:
        cells = [name] + ["NT"] * 8
    return "".join(f"<td>{c}</td>" for c in cells)


def build_coverage_data(report_type: str, xml_paths: list[Path]) -> dict:
    """Compute coverage metrics per stage using specified formulas."""
    name = DISPLAY_NAMES[report_type]
    if not xml_paths:
        return {
            "stage": name,
            "exec_rate": "NT",
            "exec_no_skip": "NT",
            "pass_rate": "NT",
        }
    # parse
    results, total, failures, skipped, _ = parse_files(xml_paths)
    executed = total - skipped
    passed   = executed - failures
    # only count skipped with reason
    skipped_with_reason = 0
    for fr in results:
        for case in fr.cases:
            if case.status == "skipped" and getattr(case, "failure_message", "").strip():
                skipped_with_reason += 1
    # formulas
    exec_rate      = (passed + failures + skipped_with_reason) / total * 100 if total else 0
    exec_no_skip   = (passed + failures) / total * 100 if total else 0
    pass_rate      = passed / total * 100 if total else 0
    return {
        "stage": name,
        "exec_rate": f"{exec_rate:.1f}",
        "exec_no_skip": f"{exec_no_skip:.1f}",
        "pass_rate": f"{pass_rate:.1f}",
    }


def _worker(task):
    """Worker for parallel report generation."""
    rtype, project, name, xmls, out_root = task
    try:
        render_report(project, name, xmls, out_root / f"{rtype}_Report.html")
        return (rtype, True, None)
    except Exception as e:
        return (rtype, False, str(e))


def main():
    parser = argparse.ArgumentParser(
        description="Generate GTest HTML reports and index with Jenkins build info"
    )
    parser.add_argument("project",    help="프로젝트명")
    parser.add_argument("input_dir",  help="in 폴더 경로")
    parser.add_argument("output_dir", help="out 폴더 경로")
    parser.add_argument("--branch",   help="Git 브랜치명",     default=None)
    parser.add_argument("--tag",      help="Release Tag",      default=None)
    parser.add_argument("--commit",   help="Commit ID",        default=None)
    parser.add_argument("--build",    help="Jenkins Build #",   default=None)
    args = parser.parse_args()

    project_name = args.project
    input_root   = Path(args.input_dir)
    output_root  = Path(args.output_dir)
    branch       = args.branch
    release_tag  = args.tag
    commit_id    = args.commit
    build_number = args.build
    report_date  = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    output_root.mkdir(parents=True, exist_ok=True)

    # 1) Parallel report generation
    tasks = []
    for rtype in REPORT_TYPES:
        xmls = list((input_root / rtype).glob("*.xml"))
        tasks.append((rtype, project_name, DISPLAY_NAMES[rtype], xmls, output_root))

    with ProcessPoolExecutor() as executor:
        future_map = {executor.submit(_worker, t): t[0] for t in tasks}
        for future in as_completed(future_map):
            rtype, success, err = future.result()
            if success:
                print(f"  → {rtype}_Report.html generated")
            else:
                print(f"[ERROR] {rtype}: {err}", file=sys.stderr)

    # 2) Build index data
    index_rows     = [
        build_index_cells(rtype, list((input_root / rtype).glob("*.xml")))
        for rtype in REPORT_TYPES
    ]
    coverage_rows = [
        build_coverage_data(rtype, list((input_root / rtype).glob("*.xml")))
        for rtype in REPORT_TYPES
    ]

    # 3) Render index.html
    tpl_dir = Path(__file__).parent / "templates"
    env     = Environment(
        loader=FileSystemLoader(str(tpl_dir)),
        autoescape=select_autoescape(["html"])
    )
    tpl = env.get_template("index.html")
    html = tpl.render(
        project_name   = project_name,
        branch         = branch,
        release_tag    = release_tag,
        commit_id      = commit_id,
        build_number   = build_number,
        report_date    = report_date,
        index_rows     = index_rows,
        coverage_rows  = coverage_rows,
    )
    (output_root / "index.html").write_text(html, encoding="utf-8")

    print(f"\nIndex generated at {output_root/'index.html'}")
    print("All reports processed successfully.")


if __name__ == "__main__":
    main()
