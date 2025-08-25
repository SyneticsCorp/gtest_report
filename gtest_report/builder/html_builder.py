import shutil
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape
from collections import defaultdict

from ..parser import parse_files
from .utils import row_html, sanitize_id, jsonify

ICON_FILES = {
    "passed": "gtest_report_ok.png",
    "success": "gtest_report_ok.png",
    "failed": "gtest_report_notok.png",
    "skipped": "gtest_report_disable.png",
}

def format_icon(status: str) -> str:
    fn = ICON_FILES.get(status, ICON_FILES["skipped"])
    return (
        f'<img src="html_resources/{fn}" alt="{status}" '
        'class="icon" width="16" height="16"/>'
    )

def aggregate_suites_by_file(results):
    suite_by_file = defaultdict(list)
    suite_status = {}
    timestamps = []

    for fr in results:
        if fr.timestamp:
            timestamps.append(fr.timestamp)
        file = fr.filename
        cases_by_suite = defaultdict(list)
        for case in fr.cases:
            suite, _ = case.name.split(".", 1)
            cases_by_suite[suite].append(case)

        for suite, cases in cases_by_suite.items():
            if any(c.status == "failed" for c in cases):
                status = "failed"
            elif all(c.status == "skipped" for c in cases):
                status = "skipped"
            else:
                status = "passed"
            suite_status[suite] = status
            suite_by_file[file].append({"suite": suite, "status": status})

    total = len(suite_status)
    failures = sum(1 for s in suite_status.values() if s == "failed")
    skipped = sum(1 for s in suite_status.values() if s == "skipped")
    return total, failures, skipped, timestamps, suite_by_file

def render_report(project_name, report_name, xml_paths, output_path,
                  sa_xml_path: Path | None = None, sa_data: dict | None = None):
    tpl_dir = Path(__file__).parent.parent / "templates"
    env = Environment(
        loader=FileSystemLoader(str(tpl_dir)),
        autoescape=select_autoescape(["html"]),
    )
    tpl = env.get_template("report.html")

    if sa_xml_path and sa_data:
        tpl_sa = env.get_template("sa_report.html")
        html = tpl_sa.render(
            title=f"{project_name} - Static Analysis Report",
            sa_total_violations=f"{sa_data.get('total_violations', 0):,}",
            sa_component_counts={k: f"{v:,}" for k, v in sa_data.get("comp_counts", {}).items()},
            sa_severity_counts={k: f"{v:,}" for k, v in sa_data.get("severity_counts", {}).items()},
            sa_ruleid_counts={k: f"{v:,}" for k, v in sa_data.get("ruleid_counts", {}).items()},
            sa_data=sa_data,
        )
        output_path.write_text(html, encoding="utf-8")
        return

    results, _, _, _, _ = parse_files(xml_paths)

    if report_name == "Unit Integration Test":
        total, failures, skipped, timestamps, suite_by_file = aggregate_suites_by_file(results)
        executed = total - skipped
        passed = executed - failures

        overall_rows = [
            row_html(["Total Test Suites", str(total)]),
            row_html(["Executed Suites", str(executed)]),
            row_html(["Passed Suites", str(passed)]),
            row_html(["Failed Suites", f'<span style="color:red;">{failures}</span>']),
            row_html(["Skipped Suites", str(skipped)]),
            row_html(["Earliest Timestamp", min(timestamps).strftime("%Y-%m-%d %H:%M:%S") if timestamps else ""]),
        ]

        failed_rows = ['<tr><th>Test Suite</th><th>Result</th></tr>']
        seen = set()
        for file, suites in suite_by_file.items():
            for suite_info in suites:
                if suite_info["status"] == "failed" and suite_info["suite"] not in seen:
                    failed_rows.append(
                        f"<tr><td>{suite_info['suite']}</td><td>{format_icon('failed')}</td></tr>"
                    )
                    seen.add(suite_info["suite"])

        detail_parts = []
        for file, suites in suite_by_file.items():
            detail_parts.append(f"<h3>{file}</h3>")
            detail_parts.append("""<table class="utests">
  <colgroup><col style="width:60%;"><col style="width:40%;"></colgroup>""")
            detail_parts.append("<tr><th>Test Suite</th><th>Result</th></tr>")
            for suite_info in suites:
                detail_parts.append(
                    f"<tr><td>{suite_info['suite']}</td><td>{format_icon(suite_info['status'])}</td></tr>"
                )
            detail_parts.append("</table>")

        charts = {
            "exec_labels": jsonify(["Execution Rate (%)"]),
            "exec_values": jsonify([round((passed + failures + skipped) / total * 100, 2)] if total else []),
            "exec_no_skip_labels": jsonify(["Execution Rate (without Skipped) (%)"]),
            "exec_no_skip_values": jsonify([round((passed + failures) / total * 100, 2)] if total else []),
            "pass_labels": jsonify(["Pass Rate (%)"]),
            "pass_values": jsonify([round(passed / total * 100, 2)] if total else []),
        }

        html = tpl.render(
            title=f"{project_name} {report_name}",
            overall_rows=overall_rows,
            failed_rows=failed_rows,
            file_rows=[],  # 제거
            test_details=detail_parts,
            **charts,
            report_name=report_name,
        )
        output_path.write_text(html, encoding="utf-8")
        return

    # UT 등 기존 로직은 그대로 유지 (필요 시 요청 주시면 포함해드립니다)

    # UT 등 기본 처리
    results, total, failures, skipped, timestamps = parse_files(xml_paths)
    executed = total - skipped
    passed = executed - failures

    skipped_with_reason = 0
    skipped_no_reason = 0
    for fr in results:
        for case in fr.cases:
            if case.status == "skipped":
                if getattr(case, "failure_message", "").strip():
                    skipped_with_reason += 1
                else:
                    skipped_no_reason += 1

    earliest = min(timestamps).strftime("%Y-%m-%d %H:%M:%S") if timestamps else ""

    res_src = Path(__file__).parent.parent / "html_resources"
    res_dst = output_path.parent / "html_resources"
    res_dst.mkdir(exist_ok=True)
    shutil.copytree(res_src, res_dst, dirs_exist_ok=True)

    overall_rows = [
        row_html(["Total XML files", str(len(results))]),
        row_html(["Total Tests", str(total)]),
        row_html(["Executed Tests", str(executed)]),
        row_html(["Execution Rate (%)", f"{(passed + failures + skipped_with_reason) / total * 100:.2f}%" if total else ""]),
        row_html(["Execution Rate (without Skipped) (%)", f"{(passed + failures) / total * 100:.2f}%" if total else ""]),
        row_html(["Pass Rate (%)", f"{passed / total * 100:.2f}%" if total else ""]),
        row_html(["Failed Tests", f'<span style="color:red;">{failures}</span>']),
        row_html(["Skipped (No Reason Specified)", str(skipped_no_reason)]),
        row_html(["Skipped (Reason Specified)", str(skipped_with_reason)]),
        row_html(["Earliest Timestamp", earliest]),
    ]

    failed_rows = ['<tr><th>Test Suite</th><th>Test Case</th><th>Result</th></tr>']
    for fr in results:
        for case in fr.cases:
            if case.status == "failed":
                suite, case_name = case.name.split(".", 1)
                aid = sanitize_id(f"{fr.filename}_{case.name}")
                link = f'<a href="#test_{aid}">{case_name}</a>'
                failed_rows.append(f"<tr><td>{suite}</td><td>{link}</td><td>{format_icon(case.status)}</td></tr>")

    file_rows = [
        '<tr><th>Test File</th><th>Total Tests</th><th>Failed</th><th>Timestamp</th></tr>'
    ]
    for fr in results:
        ts = fr.timestamp.strftime("%Y-%m-%d %H:%M:%S") if fr.timestamp else ""
        fh = f'<span style="color:red;">{fr.failures}</span>' if fr.failures else "0"
        file_rows.append(
            f"<tr><td><a href='#detail_{fr.filename}'>{fr.filename}</a></td>"
            f"<td>{fr.total}</td><td>{fh}</td><td>{ts}</td></tr>"
        )

    detail_parts = []
    for fr in results:
        detail_parts.append(f'<h3 id="detail_{fr.filename}">{fr.filename}</h3>')
        detail_parts.append("""<table class="utests">
  <colgroup>
    <col style="width:40%;">
    <col style="width:40%;">
    <col style="width:20%;">
  </colgroup>""")
        detail_parts.append('<tr><th>Test Suite</th><th>Test Case</th><th>Result</th></tr>')
        for case in fr.cases:
            suite, case_name = case.name.split(".", 1)
            aid = sanitize_id(f"{fr.filename}_{case.name}")
            detail_parts.append(
                f'<tr id="test_{aid}"><td>{suite}</td><td>{case_name}</td><td>{format_icon(case.status)}</td></tr>'
            )
        detail_parts.append("</table>")

    charts = {
        "exec_labels": jsonify(["Execution Rate (%)"]),
        "exec_values": jsonify([round((passed + failures + skipped_with_reason) / total * 100, 2)] if total else []),
        "exec_no_skip_labels": jsonify(["Execution Rate (without Skipped) (%)"]),
        "exec_no_skip_values": jsonify([round((passed + failures) / total * 100, 2)] if total else []),
        "pass_labels": jsonify(["Pass Rate (%)"]),
        "pass_values": jsonify([round(passed / total * 100, 2)] if total else []),
    }

    html = tpl.render(
        title=f"{project_name} {report_name}",
        overall_rows=overall_rows,
        failed_rows=failed_rows,
        file_rows=file_rows,
        test_details=detail_parts,
        **charts,
        report_name=report_name,
    )
    output_path.write_text(html, encoding="utf-8")
