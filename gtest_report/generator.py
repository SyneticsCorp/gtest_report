# File: gtest_report/generator.py

"""
Generates an HTML report from parsed test data and copies necessary resources.
- Bar chart 생성: matplotlib
- 템플릿 렌더링: Jinja2 + FileSystemLoader
Requires: pip install matplotlib jinja2
"""
from pathlib import Path
from datetime import datetime
import shutil
import matplotlib.pyplot as plt
from jinja2 import Environment, FileSystemLoader, select_autoescape

from .parser import parse_files

# 리소스 경로
RESOURCES_DIR = Path(__file__).parent / 'html_resources'
ICON_FILES    = {
    'success': 'gtest_report_ok.png',
    'failed':  'gtest_report_notok.png',
    'skipped': 'gtest_report_disable.png'
}

def format_icon(status: str) -> str:
    fn = ICON_FILES.get(status, ICON_FILES['skipped'])
    return f'<img src="html_resources/{fn}" alt="{status}" class="icon" width="16" height="16"/>'

def row_html(cells: list[str], header: bool=False) -> str:
    tag = 'th' if header else 'td'
    return ''.join(f'<{tag}>{c}</{tag}>' for c in cells)

def sanitize_id(text: str) -> str:
    return ''.join(c if c.isalnum() or c=='_' else '_' for c in text)

def split_test_name(full: str) -> tuple[str,str]:
    parts = full.split('.',1)
    return (parts[0], parts[1]) if len(parts)==2 else ('', full)

def generate_report(
    project_name: str,
    report_name: str,
    xml_paths: list[Path],
    output_path: Path
):
    # 파싱
    results, total, failures, skipped, timestamps = parse_files(xml_paths)
    executed  = total - skipped
    successes = executed - failures
    earliest  = min(timestamps).strftime("%Y-%m-%d %H:%M:%S") if timestamps else ''

    # 출력 폴더 및 리소스 복사
    output_path.parent.mkdir(parents=True, exist_ok=True)
    res_dir = output_path.parent / 'html_resources'
    if not res_dir.exists():
        shutil.copytree(RESOURCES_DIR, res_dir)

    # 막대 차트 생성
    values = [executed/total*100 if total else 0,
              successes/total*100 if total else 0]
    fig, ax = plt.subplots(figsize=(4,1.5))
    ax.barh(['Executed','Success'], values)
    ax.set_xlim(0,100)
    for i, v in enumerate(values):
        ax.text(v+1, i, f"{v:.1f}%", va='center')
    plt.tight_layout()
    plt.savefig(res_dir/'rate_bar.png', bbox_inches='tight')
    plt.close()

    # Overall Summary 테이블 행
    overall_rows = [
        row_html(['Total XML files',    str(len(results))]),
        row_html(['Total tests',        str(total)]),
        row_html(['Executed tests',     str(executed)]),
        row_html(['Execution rate',     f"{executed/total*100:.2f}%"]),
        row_html(['Success tests',      str(successes)]),
        row_html(['Success rate',       f"{successes/total*100:.2f}%"]),
        row_html(['Failure tests',      f'<span style="color:red;">{failures}</span>']),
        row_html(['Skipped tests',      str(skipped)]),
        row_html(['Earliest timestamp', earliest])
    ]

    # Failed Tests 테이블 행
    failed_rows = [row_html(['Report Name','Test Name'], header=True)]
    for res in results:
        for case in res.cases:
            if case.status == 'failed':
                test_id = sanitize_id(f"{res.filename}_{case.name}")
                link    = f'<a href="#test_{test_id}">{case.name}</a>'
                failed_rows.append(row_html([res.filename, link]))

    # File Summary 테이블 행
    file_rows = []
    for res in results:
        ts = res.timestamp.strftime("%Y-%m-%d %H:%M:%S") if res.timestamp else ''
        fh = f'<span style="color:red;">{res.failures}</span>' if res.failures>0 else '0'
        file_rows.append(row_html([
            f'<a href="#detail_{res.filename}">{res.filename}</a>',
            str(res.total),
            fh,
            ts
        ]))

    # Test Details by File (Suite / Case / Result)
    detail_parts = []
    for res in results:
        detail_parts.append(f'<h3 id="detail_{res.filename}">{res.filename}</h3>')
        detail_parts.append("""
<table class="utests" style="width:100%; table-layout:fixed;">
 <colgroup>
   <col style="width:40%;">
   <col style="width:40%;">
   <col style="width:20%;">
 </colgroup>
""")
        detail_parts.append(row_html(['Test Suite','Test Case','Result'], header=True))
        for case in res.cases:
            suite, case_name = split_test_name(case.name)
            row_id = f"test_{sanitize_id(res.filename)}_{sanitize_id(case.name)}"
            detail_parts.append(
                f'<tr id="{row_id}">'
                f'<td>{suite}</td>'
                f'<td>{case_name}</td>'
                f'<td>{format_icon(case.status)}</td>'
                '</tr>'
            )
        detail_parts.append('</table><br/>')

    # report.html 렌더링
    tpl_dir = Path(__file__).parent / 'templates'
    env     = Environment(
        loader=FileSystemLoader(str(tpl_dir)),
        autoescape=select_autoescape(['html'])
    )
    tpl  = env.get_template('report.html')
    html = tpl.render(
        title=f"{project_name} {report_name}",
        overall_rows=overall_rows,
        failed_rows=failed_rows,
        file_rows=file_rows,
        test_details=detail_parts
    )
    output_path.write_text(html, encoding='utf-8')
