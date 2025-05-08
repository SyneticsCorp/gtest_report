# File: gtest_report/builder/html_builder.py

"""
HTML 보고서 생성기:
- XML 파싱 결과를 받아 Overall Test Summary(메트릭 확장) 섹션 준비
- Chart.js용 3개 파이 차트 데이터 준비
- Jinja2 템플릿 렌더링
"""
import shutil
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape

from ..parser import parse_files
from .utils import row_html, sanitize_id, jsonify

ICON_FILES = {
    "success":    "gtest_report_ok.png",
    "failed":     "gtest_report_notok.png",
    "skipped":    "gtest_report_disable.png",
}


def format_icon(status: str) -> str:
    fn = ICON_FILES.get(status, ICON_FILES["skipped"])
    return (
        f'<img src="html_resources/{fn}" alt="{status}" '
        'class="icon" width="16" height="16"/>'
    )


def render_report(
    project_name: str,
    report_name: str,
    xml_paths: list[Path],
    output_path: Path,
) -> None:
    # 1) XML 파싱
    results, total, failures, skipped, timestamps = parse_files(xml_paths)
    executed = total - skipped
    passed   = executed - failures

    # 2) Skipped 분리
    skipped_with_reason = 0
    skipped_no_reason   = 0
    for fr in results:
        for case in fr.cases:
            if case.status == "skipped":
                if getattr(case, "failure_message", "").strip():
                    skipped_with_reason += 1
                else:
                    skipped_no_reason += 1

    # 3) Earliest timestamp
    earliest = (
        min(timestamps).strftime("%Y-%m-%d %H:%M:%S") if timestamps else ""
    )

    # 4) 정적 리소스 복사
    res_src = Path(__file__).parent.parent / "html_resources"
    res_dst = output_path.parent / "html_resources"
    res_dst.mkdir(exist_ok=True)
    shutil.copytree(res_src, res_dst, dirs_exist_ok=True)

    # 5) Overall Test Summary 테이블 행
    overall_rows = [
        row_html(["Total XML files", str(len(results))]),
        row_html(["Total Tests",      str(total)]),
        row_html(["Executed Tests",   str(executed)]),
        row_html([
            "Execution Rate (%)",
            f"{(passed + failures + skipped_with_reason) / total * 100:.2f}%"
            if total else ""
        ]),
        row_html([
            "Execution Rate (without Skipped) (%)",
            f"{(passed + failures) / total * 100:.2f}%"
            if total else ""
        ]),
        row_html([
            "Pass Rate (%)",
            f"{passed / total * 100:.2f}%"
            if total else ""
        ]),
        row_html(["Failed Tests",          f'<span style="color:red;">{failures}</span>']),
        row_html(["Skipped (No Reason Specified)",   str(skipped_no_reason)]),
        row_html(["Skipped (Reason Specified)",      str(skipped_with_reason)]),
        row_html(["Earliest Timestamp",    earliest]),
    ]

    # 6) Failed Test Cases
    failed_rows = [row_html(["Test Suite", "Test Case", "Result"], header=True)]
    for fr in results:
        for case in fr.cases:
            if case.status == "failed":
                suite, case_name = case.name.split(".", 1)
                aid = sanitize_id(f"{fr.filename}_{case.name}")
                link = f'<a href="#test_{aid}">{case_name}</a>'
                failed_rows.append(
                    row_html([suite, link, format_icon(case.status)])
                )

    # 7) Test File Summary
    file_rows = [
        row_html(["Test File", "Total Tests", "Failed", "Timestamp"], header=True)
    ]
    for fr in results:
        ts = fr.timestamp.strftime("%Y-%m-%d %H:%M:%S") if fr.timestamp else ""
        fh = f'<span style="color:red;">{fr.failures}</span>' if fr.failures else "0"
        file_rows.append(
            row_html([
                f'<a href="#detail_{fr.filename}">{fr.filename}</a>',
                str(fr.total),
                fh,
                ts
            ])
        )

    # 8) Detailed Test Results
    detail_parts: list[str] = []
    for fr in results:
        detail_parts.append(f'<h3 id="detail_{fr.filename}">{fr.filename}</h3>')
        detail_parts.append("""
<table class="utests">
  <colgroup>
    <col style="width:40%;">
    <col style="width:40%;">
    <col style="width:20%;">
  </colgroup>
""")
        detail_parts.append(row_html(["Test Suite", "Test Case", "Result"], header=True))
        for case in fr.cases:
            suite, case_name = case.name.split(".", 1)
            aid = sanitize_id(f"{fr.filename}_{case.name}")
            detail_parts.append(
                f'<tr id="test_{aid}">'
                + row_html([suite, case_name, format_icon(case.status)])
                + "</tr>"
            )
        detail_parts.append("</table><br/>")

    # 9) 차트용 데이터 JSON
    charts = {
        "exec_labels":      jsonify(["Execution Rate (%)"]),
        "exec_values":      jsonify([round((passed + failures + skipped_with_reason) / total * 100, 2)] if total else []),
        "exec_no_skip_labels": jsonify(["Execution Rate (without Skipped) (%)"]),
        "exec_no_skip_values": jsonify([round((passed + failures) / total * 100, 2)] if total else []),
        "pass_labels":      jsonify(["Pass Rate (%)"]),
        "pass_values":      jsonify([round(passed / total * 100, 2)] if total else []),
    }

    # 10) 템플릿 렌더링
    tpl_dir = Path(__file__).parent.parent / "templates"
    env = Environment(
        loader=FileSystemLoader(str(tpl_dir)),
        autoescape=select_autoescape(["html"]),
    )
    tpl = env.get_template("report.html")
    html = tpl.render(
        title         = f"{project_name} {report_name}",
        overall_rows  = overall_rows,
        failed_rows   = failed_rows,
        file_rows     = file_rows,
        test_details  = detail_parts,
        **charts
    )
    output_path.write_text(html, encoding="utf-8")
