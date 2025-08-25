import sys
import argparse
import re
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
from collections import defaultdict
from xml.dom.minidom import parse

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .parser import parse_files
from .builder.html_builder import render_report
from .sa_component_report_generator import generate_sa_component_reports
from .sa_summary_parser import parse_sa_file_enhanced

REPORT_TYPES  = ["UT", "UIT", "SCT", "SCIT", "SRT"]
DISPLAY_NAMES = {
    "UT":   "Unit Test",
    "UIT":  "Unit Integration Test",
    "SCT":  "Component Test",
    "SCIT": "Component Integration Test",
    "SRT":  "SW Requirement Test",
}

def _worker(task):
    rtype, project, name, xmls, out_root = task
    try:
        render_report(project, name, xmls, out_root / f"{rtype}_Report.html")
        return (rtype, True, None)
    except Exception as e:
        return (rtype, False, str(e))

def aggregate_suites_from_ut(results):
    """
    UT의 TestCaseResult 리스트로부터 Test Suite 단위 집계 수행
    Test Suite 내 하나라도 실패 케이스 있으면 Suite 전체 실패 처리.
    """
    suite_status_map = {}  # suite_name -> status ('passed','failed','skipped')
    timestamps = []

    for fr in results:
        if fr.timestamp:
            timestamps.append(fr.timestamp)
        suite_cases = defaultdict(list)
        for case in fr.cases:
            suite, _ = case.name.split('.', 1)
            suite_cases[suite].append(case)
        for suite, cases in suite_cases.items():
            if any(c.status == 'failed' for c in cases):
                suite_status_map[suite] = 'failed'
            elif all(c.status == 'skipped' for c in cases):
                if suite not in suite_status_map:
                    suite_status_map[suite] = 'skipped'
            else:
                if suite not in suite_status_map:
                    suite_status_map[suite] = 'passed'

    total_suites = len(suite_status_map)
    failures = sum(1 for s in suite_status_map.values() if s == 'failed')
    skipped = sum(1 for s in suite_status_map.values() if s == 'skipped')

    suite_results = [{'suite': suite, 'status': status} for suite, status in suite_status_map.items()]
    return total_suites, failures, skipped, timestamps, suite_results

def build_index_cells_for_uit(report_type: str, xml_paths: list[Path]) -> str:
    name = DISPLAY_NAMES[report_type]
    if xml_paths:
        results, _, _, _, timestamps = parse_files(xml_paths)
        total, failures, skipped, _, _ = aggregate_suites_from_ut(results)
        executed = total - skipped
        successes = executed - failures

        ts_str = min(timestamps).strftime("%Y-%m-%d %H:%M:%S") if timestamps else ""
        link = f'<a href="{report_type}_Report.html">View Report</a>'
        fail_html = f'<span style="color:red;">{failures:,}</span>' if failures else "0"

        cells = [
            name,
            f"{total:,}",
            f"{executed:,}",
            f"{successes:,}",
            fail_html,
            "0",  # skipped_no_reason placeholder
            "0",  # skipped_with_reason placeholder
            ts_str,
            link,
        ]
    else:
        cells = [name] + ["NT"] * 8

    return "".join(f"<td>{c}</td>" for c in cells)

def _worker_uit(task):
    rtype, project, name, xmls, out_root = task
    try:
        # UIT는 UT xmls 사용, Test Suite 단위로 집계 (필요시 커스텀 리포트 로직 추가 가능)
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
    parser.add_argument("--debug",    action="store_true", help="Enable debug mode to output etc.txt")
    args = parser.parse_args()

    project_name = args.project
    input_root = Path(args.input_dir)
    output_root = Path(args.output_dir)
    branch = args.branch
    release_tag = args.tag
    commit_id = args.commit
    build_number = args.build
    debug_mode = args.debug
    report_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    output_root.mkdir(parents=True, exist_ok=True)

    print(f"Starting report generation for project: {project_name}")
    print(f"Input: {input_root}, Output: {output_root}\n")

    tasks = []
    for rtype in REPORT_TYPES:
        if rtype == "UIT":
            xmls = list((input_root / "UT").glob("*.xml"))
            cells_func = build_index_cells_for_uit
            worker_func = _worker_uit
        else:
            xmls = list((input_root / rtype).glob("*.xml"))
            cells_func = build_index_cells
            worker_func = _worker

        print(f"Processing {rtype} ({DISPLAY_NAMES[rtype]}): {len(xmls)} XML files found.")
        tasks.append((rtype, project_name, DISPLAY_NAMES[rtype], xmls, output_root))

    with ProcessPoolExecutor() as executor:
        future_map = {executor.submit(worker_func, t): t[0] for t in tasks}
        for future in as_completed(future_map):
            rtype, success, err = future.result()
            if success:
                print(f"  → {rtype}_Report.html generated")
            else:
                print(f"[ERROR] {rtype}: {err}", file=sys.stderr)

    index_rows = [
        build_index_cells_for_uit(rtype, list((input_root / "UT").glob("*.xml"))) if rtype == "UIT" else build_index_cells(rtype, list((input_root / rtype).glob("*.xml")))

        for rtype in REPORT_TYPES
    ]

    # SA 보고서 처리
    sa_report_path = input_root / "SA" / "report.xml"
    sa_data = {}

    if sa_report_path.exists():
        print(f"Processing Static Analysis report: {sa_report_path}")
        sa_data = parse_sa_file_enhanced(sa_report_path, debug=debug_mode)
        render_report(
            project_name,
            "Static Analysis",
            [],
            output_root / "SA_Report.html",
            sa_xml_path=sa_report_path,
            sa_data=sa_data,
        )
        print("  → SA_Report.html generated")

        generate_sa_component_reports(sa_report_path, output_root)
        print("  → SA Component detailed reports generated")
    else:
        print("No Static Analysis report found.")

    tpl_dir = Path(__file__).parent / "templates"
    env = Environment(
        loader=FileSystemLoader(str(tpl_dir)),
        autoescape=select_autoescape(["html"])
    )
    
    # Generate improved version as main (index.html) - using inline styles for Jenkins CSP compatibility
    try:
        # Try to use inline style template for Jenkins CSP compatibility
        tpl_improved = env.get_template("index_compact_inline.html")
        html_improved = tpl_improved.render(
            project_name=project_name,
            branch=branch,
            release_tag=release_tag,
            commit_id=commit_id,
            build_number=build_number,
            report_date=report_date,
            index_rows=index_rows,
            sa_total_violations=f"{sa_data.get('total_violations', 0):,}" if sa_data else "0",
            sa_component_counts={k: f"{v:,}" for k, v in sa_data.get("comp_counts", {}).items()} if sa_data else {},
        )
        (output_root / "index.html").write_text(html_improved, encoding="utf-8")
        print(f"\nImproved index (inline styles) generated at {output_root / 'index.html'}")
    except Exception:
        # Fallback to compact template if inline not found
        try:
            tpl_compact = env.get_template("index_compact.html")
            html_compact = tpl_compact.render(
                project_name=project_name,
                branch=branch,
                release_tag=release_tag,
                commit_id=commit_id,
                build_number=build_number,
                report_date=report_date,
                index_rows=index_rows,
                sa_total_violations=f"{sa_data.get('total_violations', 0):,}" if sa_data else "0",
                sa_component_counts={k: f"{v:,}" for k, v in sa_data.get("comp_counts", {}).items()} if sa_data else {},
            )
            (output_root / "index.html").write_text(html_compact, encoding="utf-8")
            print(f"\nCompact index generated at {output_root / 'index.html'}")
        except Exception:
            # Final fallback to original template
            tpl_main = env.get_template("index.html")
            html_main = tpl_main.render(
                project_name=project_name,
                branch=branch,
                release_tag=release_tag,
                commit_id=commit_id,
                build_number=build_number,
                report_date=report_date,
                index_rows=index_rows,
                sa_total_violations=f"{sa_data.get('total_violations', 0):,}" if sa_data else "0",
                sa_component_counts={k: f"{v:,}" for k, v in sa_data.get("comp_counts", {}).items()} if sa_data else {},
            )
            (output_root / "index.html").write_text(html_main, encoding="utf-8")
            print(f"\nMain index generated at {output_root / 'index.html'}")
    
    # Always generate original version as index_original.html
    tpl_original = env.get_template("index.html")
    html_original = tpl_original.render(
        project_name=project_name,
        branch=branch,
        release_tag=release_tag,
        commit_id=commit_id,
        build_number=build_number,
        report_date=report_date,
        index_rows=index_rows,
        sa_total_violations=f"{sa_data.get('total_violations', 0):,}" if sa_data else "0",
        sa_component_counts={k: f"{v:,}" for k, v in sa_data.get("comp_counts", {}).items()} if sa_data else {},
    )
    (output_root / "index_original.html").write_text(html_original, encoding="utf-8")
    print(f"Original index generated at {output_root / 'index_original.html'}")
    
    # Also generate compact version with external CSS for environments without CSP
    try:
        tpl_compact_ext = env.get_template("index_compact.html")
        html_compact_ext = tpl_compact_ext.render(
            project_name=project_name,
            branch=branch,
            release_tag=release_tag,
            commit_id=commit_id,
            build_number=build_number,
            report_date=report_date,
            index_rows=index_rows,
            sa_total_violations=f"{sa_data.get('total_violations', 0):,}" if sa_data else "0",
            sa_component_counts={k: f"{v:,}" for k, v in sa_data.get("comp_counts", {}).items()} if sa_data else {},
        )
        (output_root / "index_compact_external.html").write_text(html_compact_ext, encoding="utf-8")
        print(f"Compact index (external CSS) generated at {output_root / 'index_compact_external.html'}")
    except Exception:
        pass
    
    print("All reports processed successfully.")

def build_index_cells(report_type: str, xml_paths: list[Path]) -> str:
    name = DISPLAY_NAMES[report_type]
    if xml_paths:
        results, total, failures, skipped, timestamps = parse_files(xml_paths)
        executed = total - skipped
        successes = executed - failures

        skipped_with_reason = 0
        skipped_no_reason = 0
        for fr in results:
            for case in fr.cases:
                if case.status == "skipped":
                    if getattr(case, "failure_message", "").strip():
                        skipped_with_reason += 1
                    else:
                        skipped_no_reason += 1

        ts_str = min(timestamps).strftime("%Y-%m-%d %H:%M:%S") if timestamps else ""
        link = f'<a href="{report_type}_Report.html">View Report</a>'
        fail_html = f'<span style="color:red;">{failures:,}</span>' if failures else "0"

        cells = [
            name,
            f"{total:,}",
            f"{executed:,}",
            f"{successes:,}",
            fail_html,
            f"{skipped_no_reason:,}",
            f"{skipped_with_reason:,}",
            ts_str,
            link,
        ]
    else:
        cells = [name] + ["NT"] * 8

    return "".join(f"<td>{c}</td>" for c in cells)

if __name__ == "__main__":
    main()
