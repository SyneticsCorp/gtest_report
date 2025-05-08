# File: gtest_report/builder/__init__.py

"""
gtest_report.builder 패키지
- HTML 보고서 생성에 필요한 유틸, 차트 빌더, HTML 빌더 모듈을 묶어서 노출합니다.
"""

from .utils import row_html, sanitize_id, jsonify
from .chart_builder import build_chart_data
from .html_builder import render_report

__all__ = [
    "row_html",
    "sanitize_id",
    "jsonify",
    "build_chart_data",
    "render_report",
]
