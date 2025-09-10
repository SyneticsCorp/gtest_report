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

def generate_module_original_reports(project_name, input_root, output_root, branch=None, tag=None, commit=None, build=None):
    """Generate module-specific original reports (para-exec, para-diag, para-com)"""
    report_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    modules = ["exec", "diag", "com"]
    
    tpl_dir = Path(__file__).parent / "templates"
    env = Environment(
        loader=FileSystemLoader(str(tpl_dir)),
        autoescape=select_autoescape(["html"])
    )
    tpl_original = env.get_template("index.html")
    
    for module in modules:
        print(f"\nGenerating {module.upper()} module original report...")
        
        # Filter XML files for this module
        module_xmls = {}
        total_files = 0
        for rtype in REPORT_TYPES:
            type_dir = input_root / rtype
            if type_dir.exists():
                # Match files containing the module name (para_exec, para_diag, para_com)
                pattern = f"para_{module}*"
                xmls = list(type_dir.glob(pattern))
                module_xmls[rtype] = xmls
                total_files += len(xmls)
                print(f"  {rtype}: {len(xmls)} files for {module}")
        
        if total_files == 0:
            print(f"  No XML files found for {module} module, skipping...")
            continue
            
        # Generate individual reports for each test type in this module
        module_output_dir = output_root / f"{module}_reports"
        module_output_dir.mkdir(exist_ok=True)
        
        tasks = []
        for rtype in REPORT_TYPES:
            xmls = module_xmls.get(rtype, [])
            if xmls:
                if rtype == "UIT":
                    worker_func = _worker_uit
                else:
                    worker_func = _worker
                tasks.append((rtype, project_name, DISPLAY_NAMES[rtype], xmls, module_output_dir))
        
        # Execute report generation tasks for this module
        with ProcessPoolExecutor() as executor:
            future_map = {executor.submit(_worker if t[0] != "UIT" else _worker_uit, t): t[0] for t in tasks}
            for future in as_completed(future_map):
                rtype, success, err = future.result()
                if success:
                    print(f"    → {rtype}_Report.html generated for {module}")
                else:
                    print(f"    [ERROR] {rtype}: {err}", file=sys.stderr)
        
        # Generate index rows for this module
        index_rows = []
        for rtype in REPORT_TYPES:
            xmls = module_xmls.get(rtype, [])
            if rtype == "UIT":
                # For UIT, use UT files if available
                ut_xmls = module_xmls.get("UT", [])
                row = build_index_cells_for_uit(rtype, ut_xmls)
            else:
                row = build_index_cells(rtype, xmls)
            index_rows.append(row)
        
        # Generate module-specific original index
        html_content = tpl_original.render(
            project_name=f"{project_name} - {module.upper()} Module",
            branch=branch,
            release_tag=tag,
            commit_id=commit,
            build_number=build,
            report_date=report_date,
            index_rows=index_rows,
            sa_total_violations="0",  # No SA for module reports
            sa_component_counts={},
        )
        
        # Save module-specific original index
        module_index_path = output_root / f"index_original_{module}.html"
        module_index_path.write_text(html_content, encoding="utf-8")
        print(f"    → Original index generated: index_original_{module}.html")

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

    # Generate index rows with module breakdown
    index_rows = []
    for rtype in REPORT_TYPES:
        # Get all module rows for this test type
        if rtype == "UIT":
            # UIT uses UT XML files
            xmls = list((input_root / "UT").glob("*.xml"))
        else:
            xmls = list((input_root / rtype).glob("*.xml"))
        
        module_rows = build_index_cells_with_modules(rtype, xmls, include_total=True)
        index_rows.extend(module_rows)

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
    
    # Always generate original version as index_original.html (integrated view)
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
    print(f"Original index (integrated) generated at {output_root / 'index_original.html'}")
    
    # Generate module-specific original reports
    print("\nGenerating module-specific original reports...")
    generate_module_original_reports(
        project_name=project_name,
        input_root=input_root,
        output_root=output_root,
        branch=branch,
        tag=release_tag,
        commit=commit_id,
        build=build_number
    )
    
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

def build_index_cells_with_modules(report_type: str, xml_paths: list[Path], include_total: bool = False) -> list[str]:
    """Build index cells with module breakdown (returns multiple rows)"""
    name = DISPLAY_NAMES[report_type]
    modules = ["exec", "diag", "com"]
    rows = []
    
    if not xml_paths:
        # No XML files found - maintain original 9 column structure
        cells = [name, "NT", "NT", "NT", "NT", "NT", "NT", "", ""]
        return ["".join(f"<td>{c}</td>" for c in cells)]
    
    # Group XML files by module
    module_xmls = {}
    
    for module in modules:
        module_files = [xml for xml in xml_paths if f"para_{module}" in xml.name]
        if module_files:
            module_xmls[module] = module_files
    
    # If no module-specific files found, show as single row
    if not module_xmls:
        # Fall back to original single row display
        return [build_index_cells(report_type, xml_paths)]
    
    row_count = 0
    total_all = 0
    executed_all = 0
    successes_all = 0
    failures_all = 0
    skipped_no_reason_all = 0
    skipped_with_reason_all = 0
    all_timestamps = []
    
    # Process each module
    for module in modules:  # Keep order: exec, diag, com
        if module not in module_xmls:
            continue
            
        files = module_xmls[module]
        try:
            results, total, failures, skipped, timestamps = parse_files(files)
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

            # Accumulate totals
            total_all += total
            executed_all += executed
            successes_all += successes
            failures_all += failures
            skipped_no_reason_all += skipped_no_reason
            skipped_with_reason_all += skipped_with_reason
            if timestamps:
                all_timestamps.extend(timestamps)

            ts_str = min(timestamps).strftime("%Y-%m-%d %H:%M:%S") if timestamps else ""
            fail_html = f'<span style="color:red;">{failures:,}</span>' if failures else "0"
            
            # First row shows test type name + module, subsequent rows show empty + module
            if row_count == 0:
                display_name = f"{name} - {module.upper()}"
            else:
                display_name = f"&nbsp;&nbsp;&nbsp;&nbsp;{module.upper()}"  # Indent for clarity
            
            cells = [
                display_name,
                f"{total:,}",
                f"{executed:,}",
                f"{successes:,}",
                fail_html,
                f"{skipped_no_reason:,}",
                f"{skipped_with_reason:,}",
                ts_str,
                "",  # No link for individual module rows
            ]
            
            rows.append("".join(f"<td>{c}</td>" for c in cells))
            row_count += 1
            
        except Exception as e:
            print(f"Error processing {module} module for {report_type}: {e}")
    
    # Add TOTAL row if requested and we have multiple modules
    if include_total and row_count > 0:
        ts_str_total = min(all_timestamps).strftime("%Y-%m-%d %H:%M:%S") if all_timestamps else ""
        fail_html_total = f'<span style="color:red;font-weight:bold">{failures_all:,}</span>' if failures_all else "<b>0</b>"
        
        total_cells = [
            f"&nbsp;&nbsp;&nbsp;&nbsp;<b>TOTAL</b>",  # Indented TOTAL
            f"<b>{total_all:,}</b>",
            f"<b>{executed_all:,}</b>",
            f"<b>{successes_all:,}</b>",
            fail_html_total,
            f"<b>{skipped_no_reason_all:,}</b>",
            f"<b>{skipped_with_reason_all:,}</b>",
            ts_str_total,
            f'<a href="{report_type}_Report.html">View Report</a>',  # Link on total row
        ]
        
        rows.append("".join(f"<td>{c}</td>" for c in total_cells))
    
    return rows if rows else ["<td>" + name + "</td>" + "<td>No data</td>" * 8]

def build_index_cells(report_type: str, xml_paths: list[Path]) -> str:
    """Legacy function - returns first row only for backward compatibility"""
    rows = build_index_cells_with_modules(report_type, xml_paths)
    return rows[0] if rows else ""

if __name__ == "__main__":
    main()
