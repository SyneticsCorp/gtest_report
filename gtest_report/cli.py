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

def parse_sa_file_enhanced(report_xml_path: Path, debug: bool = False):
    """
    PC Lint Plus report.xml 파싱
    컴포넌트별, 심각도별 통계 + 룰 ID별 위반 수 추가
    """
    from xml.dom.minidom import parse
    from collections import defaultdict
    from pathlib import Path

    dom = parse(str(report_xml_path))
    messages = dom.getElementsByTagName("message")

    comp_counts = defaultdict(int)
    comp_files = defaultdict(set)
    severity_counts = defaultdict(int)
    ruleid_counts = defaultdict(int)
    etc_files = []

    ruleid_pattern = re.compile(r"\[AUTOSAR Rule ([^\]]+)\]")

    for msg in messages:
        # 파일/컴포넌트 추출
        file_node = msg.getElementsByTagName("file")
        if not file_node or file_node[0].firstChild is None:
            continue
        file_path = file_node[0].firstChild.nodeValue.strip()
        parts = Path(file_path).parts
        component = "etc"
        try:
            idx = parts.index("para-api")
            if idx + 1 < len(parts):
                component = parts[idx + 1]
        except ValueError:
            pass

        comp_counts[component] += 1
        comp_files[component].add(file_path)

        # 심각도 추출
        type_node = msg.getElementsByTagName("type")
        if type_node and type_node[0].firstChild:
            severity = type_node[0].firstChild.nodeValue.strip()
        else:
            severity = "Unknown"
        severity_counts[severity] += 1

        # 룰ID 추출 (desc 태그)
        desc_node = msg.getElementsByTagName("desc")
        ruleid = "etc"
        if desc_node and desc_node[0].firstChild:
            desc_text = desc_node[0].firstChild.nodeValue.strip()
            m = ruleid_pattern.search(desc_text)
            if m:
                ruleid = m.group(1)
        ruleid_counts[ruleid] += 1

        if component == "etc":
            etc_files.append(file_path)

    if debug and etc_files:
        with open("etc.txt", "w", encoding="utf-8") as f:
            for fp in etc_files:
                f.write(fp + "\n")

    return {
        "total_components": len(comp_counts),
        "total_files": sum(len(v) for v in comp_files.values()),
        "comp_files_count": {k: len(v) for k, v in comp_files.items()},
        "total_violations": sum(comp_counts.values()),
        "comp_counts": dict(comp_counts),
        "severity_counts": dict(severity_counts),
        "ruleid_counts": dict(ruleid_counts),
    }

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
        xmls = list((input_root / rtype).glob("*.xml"))
        print(f"Processing {rtype} ({DISPLAY_NAMES[rtype]}): {len(xmls)} XML files found.")
        tasks.append((rtype, project_name, DISPLAY_NAMES[rtype], xmls, output_root))

    with ProcessPoolExecutor() as executor:
        future_map = {executor.submit(_worker, t): t[0] for t in tasks}
        for future in as_completed(future_map):
            rtype, success, err = future.result()
            if success:
                print(f"  → {rtype}_Report.html generated")
            else:
                print(f"[ERROR] {rtype}: {err}", file=sys.stderr)

    # SA 보고서 처리 (기존 부분)
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

        # **컴포넌트별 상세 보고서 생성 추가**
        generate_sa_component_reports(sa_report_path, output_root)
        print("  → SA Component detailed reports generated")
    else:
        print("No Static Analysis report found.")

    index_rows = [
        build_index_cells(rtype, list((input_root / rtype).glob("*.xml")))
        for rtype in REPORT_TYPES
    ]

    tpl_dir = Path(__file__).parent / "templates"
    env = Environment(
        loader=FileSystemLoader(str(tpl_dir)),
        autoescape=select_autoescape(["html"])
    )
    tpl = env.get_template("index.html")
    html = tpl.render(
        project_name=project_name,
        branch=branch,
        release_tag=release_tag,
        commit_id=commit_id,
        build_number=build_number,
        report_date=report_date,
        index_rows=index_rows,
        sa_total_violations=sa_data.get("total_violations", 0) if sa_data else 0,
        sa_component_counts=sa_data.get("comp_counts", {}) if sa_data else {},
    )
    (output_root / "index.html").write_text(html, encoding="utf-8")
    print(f"\nIndex generated at {output_root / 'index.html'}")
    print("All reports processed successfully.")

if __name__ == "__main__":
    main()
