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

REPORT_TYPES  = ["UT", "UIT"]
DISPLAY_NAMES = {
    "UT":   "Unit Test",
    "UIT":  "Unit Integration Test",
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
    UT??TestCaseResult 由ъ뒪?몃줈遺??Test Suite ?⑥쐞 吏묎퀎 ?섑뻾
    Test Suite ???섎굹?쇰룄 ?ㅽ뙣 耳?댁뒪 ?덉쑝硫?Suite ?꾩껜 ?ㅽ뙣 泥섎━.
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
    # For the simplified dashboard we use the same simple row format
    return build_index_cells_simple(report_type, xml_paths)

def build_index_cells_simple(report_type: str, xml_paths: list[Path]) -> str:
    """
    Build a 9-cell row for improved index template:
    [Name, Total, Executed, Passed, Failed, Skipped(No), Skipped(Yes), Timestamp, Link]
    """
    name = DISPLAY_NAMES[report_type]
    if not xml_paths:
        cells = [name] + ["NT"] * 8
        return "".join(f"<td>{c}</td>" for c in cells)

    results, total, failures, _skipped_total, timestamps = parse_files(xml_paths)
    skipped_with_reason = 0
    skipped_no_reason = 0
    for fr in results:
        for case in fr.cases:
            if case.status == "skipped":
                if getattr(case, "failure_message", "").strip():
                    skipped_with_reason += 1
                else:
                    skipped_no_reason += 1

    executed = total - (skipped_no_reason + skipped_with_reason)
    passed = executed - failures
    ts_str = min(timestamps).strftime("%Y-%m-%d %H:%M:%S") if timestamps else ""
    fail_html = f"<span style='color:red;'>{failures:,}</span>" if failures else "0"
    link = f'<a href="{report_type}_Report.html">View Report</a>'

    cells = [
        name,
        f"{total:,}",
        f"{executed:,}",
        f"{passed:,}",
        fail_html,
        f"{skipped_no_reason:,}",
        f"{skipped_with_reason:,}",
        ts_str,
        link,
    ]
    return "".join(f"<td>{c}</td>" for c in cells)
def _worker_uit(task):
    rtype, project, name, xmls, out_root = task
    try:
        render_report(project, name, xmls, out_root / f"{rtype}_Report.html")
        return (rtype, True, None)
    except Exception as e:
        return (rtype, False, str(e))

def collect_module_test_data(input_root):
    """Collect test data for each module (exec, diag, com)"""
    from .parser import parse_files
    
    modules = ["exec", "diag", "com"]
    module_data = []
    
    for module in modules:
        module_stats = {
            'name': f"para-{module}",
            'total': 0,
            'executed': 0,
            'passed': 0,
            'failed': 0,
            'skipped_no_reason': 0,
            'skipped_with_reason': 0
        }
        
        # Collect data from all test types for this module
        for rtype in REPORT_TYPES:
            type_dir = input_root / rtype
            if type_dir.exists():
                # Match files containing the module name
                pattern = f"para_{module}*"
                xmls = list(type_dir.glob(pattern))
                
                if xmls:
                    results, total, failures, skipped, _ = parse_files(xmls)
                    
                    # Count skipped with/without reason
                    skipped_with_reason = 0
                    skipped_no_reason = 0
                    for fr in results:
                        for case in fr.cases:
                            if case.status == "skipped":
                                if getattr(case, "failure_message", "").strip():
                                    skipped_with_reason += 1
                                else:
                                    skipped_no_reason += 1
                    
                    module_stats['total'] += total
                    module_stats['failed'] += failures
                    module_stats['skipped_no_reason'] += skipped_no_reason
                    module_stats['skipped_with_reason'] += skipped_with_reason
                    module_stats['executed'] += (total - skipped_no_reason - skipped_with_reason)
                    module_stats['passed'] += (total - failures - skipped_no_reason - skipped_with_reason)
        
        module_data.append(module_stats)
    
    return module_data

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
                    print(f"    ??{rtype}_Report.html generated for {module}")
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
        print(f"    ??Original index generated: index_original_{module}.html")

def main():
    parser = argparse.ArgumentParser(
        description="Generate GTest HTML reports and index with Jenkins build info"
    )
    parser.add_argument("project",    help="Project name to display")
    parser.add_argument("input_dir",  help="Path to input folder (in)")
    parser.add_argument("output_dir", help="Path to output folder (out)")
    parser.add_argument("--branch",   help="Git branch name",    default=None)
    parser.add_argument("--tag",      help="Release Tag",        default=None)
    parser.add_argument("--commit",   help="Commit SHA",         default=None)
    parser.add_argument("--build",    help="Jenkins Build #",    default=None)
    parser.add_argument("--debug",    action="store_true", help="Enable debug mode to output etc.txt")
    args = parser.parse_args()

    project_name = args.project
    if isinstance(project_name, str) and project_name.strip().upper() == "PARA":
        project_name = "AutosarIO"
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
    folder_map = {"UT": "unit", "UIT": "uit"}
    for rtype in REPORT_TYPES:
        sub = folder_map[rtype]
        xmls = list((input_root / sub).glob("*.xml"))
        worker_func = _worker_uit if rtype == "UIT" else _worker
        print(f"Processing {rtype} ({DISPLAY_NAMES[rtype]}): {len(xmls)} XML files found from '{sub}/'.")
        tasks.append((rtype, project_name, DISPLAY_NAMES[rtype], xmls, output_root))

    with ProcessPoolExecutor() as executor:
        future_map = {executor.submit(worker_func, t): t[0] for t in tasks}
        for future in as_completed(future_map):
            rtype, success, err = future.result()
            if success:
                print(f"  ??{rtype}_Report.html generated")
            else:
                print(f"[ERROR] {rtype}: {err}", file=sys.stderr)

    # Build minimal index rows (no module/SA)
    index_rows = []
    for rtype in REPORT_TYPES:
        sub = folder_map[rtype]
        xmls = list((input_root / sub).glob("*.xml"))
        index_rows.append(build_index_cells_simple(rtype, xmls))

    tpl_dir = Path(__file__).parent / "templates"
    env = Environment(
        loader=FileSystemLoader(str(tpl_dir)),
        autoescape=select_autoescape(["html"])
    )
    
    # Generate improved index (cards/table layout)
    try:
        tpl_index = env.get_template("index_jenkins.html")
    except Exception:
        tpl_index = env.get_template("index_minimal_inline.html")

    html_index = tpl_index.render(
        project_name=project_name,
        branch=branch,
        release_tag=release_tag,
        commit_id=commit_id,
        build_number=build_number,
        report_date=report_date,
        index_rows=index_rows,
        sa_total_violations="0",
        sa_component_counts={},
    )
    (output_root / "index.html").write_text(html_index, encoding="utf-8")
    print(f"\nIndex generated at {output_root / 'index.html'} (improved template)")

    # Also generate compact external variant for environments without CSP constraints
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
        )
        (output_root / "index_compact_external.html").write_text(html_compact_ext, encoding="utf-8")
        print(f"Compact index (external CSS) generated at {output_root / 'index_compact_external.html'}")
    except Exception:
        pass

    print("All reports processed successfully.")
    return

def build_index_cells_with_modules(report_type: str, xml_paths: list[Path], include_total: bool = False) -> list[str]:
    """Build index cells with module breakdown (returns multiple rows)"""
    name = DISPLAY_NAMES[report_type]
    modules = ["exec", "diag", "com"]
    rows = []

    if not xml_paths:
        # No XML files found - new 9 column structure
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
    
    # Add test type header row first
    header_cells = [
        f"<b>{name}</b>",  # Test type name in bold
        "",  # Empty for other columns
        "",
        "",
        "",
        "",
        "",
        "",
        "",
    ]
    rows.append("".join(f"<td>{c}</td>" for c in header_cells))
    
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

            # Calculate rates
            exec_rate = f"{(executed / total * 100):.1f}%" if total > 0 else "0.0%"
            pass_rate = f"{(successes / (successes + failures) * 100):.1f}%" if (successes + failures) > 0 else "0.0%"
            skipped_total = skipped_no_reason + skipped_with_reason

            # Module rows are indented
            display_name = f"&nbsp;&nbsp;&nbsp;&nbsp;{module.upper()}"

            cells = [
                display_name,
                f"{total:,}",
                f"{executed:,}",
                exec_rate,
                pass_rate,
                fail_html,
                f"{skipped_total:,}",
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

        # Calculate total rates
        exec_rate_total = f"<b>{(executed_all / total_all * 100):.1f}%</b>" if total_all > 0 else "<b>0.0%</b>"
        pass_rate_total = f"<b>{(successes_all / (successes_all + failures_all) * 100):.1f}%</b>" if (successes_all + failures_all) > 0 else "<b>0.0%</b>"
        skipped_total_all = skipped_no_reason_all + skipped_with_reason_all

        total_cells = [
            f"&nbsp;&nbsp;&nbsp;&nbsp;<b>TOTAL</b>",  # Indented TOTAL
            f"<b>{total_all:,}</b>",
            f"<b>{executed_all:,}</b>",
            exec_rate_total,
            pass_rate_total,
            fail_html_total,
            f"<b>{skipped_total_all:,}</b>",
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


