# File: gtest_report/builder/html_builder.py

"""
HTML 보고서 생성기:
- XML 파싱 결과를 받아 Overall/Failed/File/Details 섹션을 준비
- Chart.js용 데이터 확보
- Jinja2 템플릿 렌더링
"""
import shutil
from pathlib import Path
from datetime import datetime
from jinja2 import Environment, FileSystemLoader, select_autoescape

from ..parser import parse_files, TestFileResult
from .utils import row_html, sanitize_id
from .chart_builder import build_chart_data

ICON_FILES = {
    "success": "gtest_report_ok.png",
    "failed": "gtest_report_notok.png",
    "skipped": "gtest_report_disable.png",
}


def format_icon(status: str) -> str:
    """
    상태에 맞는 아이콘 <img> 태그 반환.
    """
    fn = ICON_FILES.get(status, ICON_FILES["skipped"])
    return f'<img src="html_resources/{fn}" alt="{status}" class="icon" width="16" height="16"/>'


def render_report(
    project_name: str,
    report_name: str,
    xml_paths: list[Path],
    output_path: Path,
) -> None:
    # 1) XML 파싱
    results, total, failures, skipped, timestamps = parse_files(xml_paths)
    executed = total - skipped
    successes = executed - failures
    earliest = min(timestamps).strftime("%Y-%m-%d %H:%M:%S") if timestamps else ""

    # 2) 정적 리소스 복사
    res_src = Path(__file__).parent.parent / "html_resources"
    res_dst = output_path.parent / "html_resources"
    res_dst.mkdir(exist_ok=True)
    shutil.copytree(res_src, res_dst, dirs_exist_ok=True)

    # 3) Overall Summary
    overall_rows = [
        row_html(["Total XML files", str(len(results))]),
        row_html(["Total tests", str(total)]),
        row_html(["Executed tests", str(executed)]),
        row_html(["Execution rate", f"{executed/total*100:.2f}%"]),
        row_html(["Success tests", str(successes)]),
        row_html(["Success rate", f"{successes/total*100:.2f}%"]),
        row_html(["Failure tests", f'<span style="color:red;">{failures}</span>']),
        row_html(["Skipped tests", str(skipped)]),
        row_html(["Earliest timestamp", earliest]),
    ]

    # 4) Failed Tests
    failed_rows = [row_html(["Test Suite", "Test Case", "Result"], header=True)]
    for file_res in results:
        for case in file_res.cases:
            if case.status == "failed":
                suite, case_name = case.name.split(".", 1)
                anchor = sanitize_id(f"{file_res.filename}_{case.name}")
                link = f'<a href="#test_{anchor}">{case_name}</a>'
                failed_rows.append(row_html([suite, link, format_icon(case.status)]))

    # 5) File Summary
    file_rows = [
        row_html(["Report Name", "Total", "Failure", "Timestamp"], header=True)
    ]
    for file_res in results:
        ts = (
            file_res.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            if file_res.timestamp
            else ""
        )
        fh = (
            f'<span style="color:red;">{file_res.failures}</span>'
            if file_res.failures
            else "0"
        )
        file_rows.append(
            row_html(
                [
                    f'<a href="#detail_{file_res.filename}">{file_res.filename}</a>',
                    str(file_res.total),
                    fh,
                    ts,
                ]
            )
        )

    # 6) Test Details
    detail_parts: list[str] = []
    for file_res in results:
        detail_parts.append(
            f'<h3 id="detail_{file_res.filename}">{file_res.filename}</h3>'
        )
        detail_parts.append(
            """
<table class="utests">
  <colgroup>
    <col style="width:40%;">
    <col style="width:40%;">
    <col style="width:20%;">
  </colgroup>
"""
        )
        detail_parts.append(
            row_html(["Test Suite", "Test Case", "Result"], header=True)
        )
        for case in file_res.cases:
            suite, case_name = case.name.split(".", 1)
            anchor = sanitize_id(f"{file_res.filename}_{case.name}")
            detail_parts.append(
                f'<tr id="test_{anchor}">'
                + row_html([suite, case_name, format_icon(case.status)])
                + "</tr>"
            )
        detail_parts.append("</table><br/>")

    # 7) Chart.js 데이터 준비
    chart_ctx = build_chart_data(executed, skipped, successes, failures)

    # 8) 템플릿 렌더링
    tpl_dir = Path(__file__).parent.parent / "templates"
    env = Environment(
        loader=FileSystemLoader(str(tpl_dir)),
        autoescape=select_autoescape(["html"]),
    )
    tpl = env.get_template("report.html")
    html = tpl.render(
        title=f"{project_name} {report_name}",
        overall_rows=overall_rows,
        failed_rows=failed_rows,
        file_rows=file_rows,
        test_details=detail_parts,
        **chart_ctx,
    )
    output_path.write_text(html, encoding="utf-8")
