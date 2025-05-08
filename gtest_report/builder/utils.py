# File: gtest_report/builder/utils.py

"""
공통 유틸리티 함수 모음:
- HTML 셀 생성
- 안전한 HTML ID 생성
- Python 객체 → JSON 문자열
"""
import json
from typing import Any, List


def row_html(cells: List[str], header: bool = False) -> str:
    """
    주어진 문자열 리스트로 <th> 또는 <td> 셀을 만들어 이어붙여 리턴.
    header=True 이면 <th>, 아니면 <td>.
    """
    tag = "th" if header else "td"
    return "".join(f"<{tag}>{c}</{tag}>" for c in cells)


def sanitize_id(text: str) -> str:
    """
    HTML anchor 용 안전한 ID 생성:
    영문자/숫자/_ 이외 문자는 '_' 로 대체.
    """
    return "".join(c if c.isalnum() or c == "_" else "_" for c in text)


def jsonify(obj: Any) -> str:
    """
    Python 객체를 JSON 문자열로 직렬화.
    Chart.js 에 직접 삽입하기 용이하게 만듦.
    """
    return json.dumps(obj)
