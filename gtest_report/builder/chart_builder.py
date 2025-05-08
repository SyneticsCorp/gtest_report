# File: gtest_report/builder/chart_builder.py

"""
Chart.js용 데이터 준비:
- Execution Rate (Executed vs Skipped)
- Success Rate  (Success  vs Failure)
"""
from typing import Dict

from .utils import jsonify


def build_chart_data(
    executed: int, skipped: int, successes: int, failures: int
) -> Dict[str, str]:
    """
    차트 템플릿에 넘길 JSON 문자열 딕셔너리 반환.
    """
    exec_labels = ["Executed", "Skipped"]
    exec_values = [executed, skipped]
    succ_labels = ["Success", "Failure"]
    succ_values = [successes, failures]

    return {
        "exec_labels": jsonify(exec_labels),
        "exec_values": jsonify(exec_values),
        "succ_labels": jsonify(succ_labels),
        "succ_values": jsonify(succ_values),
    }
