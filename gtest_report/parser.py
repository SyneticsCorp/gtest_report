# File: gtest_report/parser.py

"""
Google Test XML 파일을 파싱하여 결과 객체(TestFileResult, TestCaseResult)로 반환
"""
from xml.dom.minidom import parse
from xml.parsers.expat import ExpatError
from datetime import datetime
from pathlib import Path

class TestCaseResult:
    def __init__(self, name: str, time: float, status: str, failure_message: str = ""):
        self.name = name
        self.time = time
        self.status = status
        self.failure_message = failure_message

class TestFileResult:
    def __init__(
        self,
        filename: str,
        total: int,
        failures: int,
        skipped: int,
        duration: float,
        timestamp: datetime | None,
        cases: list[TestCaseResult]
    ):
        self.filename  = filename
        self.total     = total
        self.failures  = failures
        self.skipped   = skipped
        self.duration  = duration
        self.timestamp = timestamp
        self.cases     = cases

def parse_file(xml_path: Path | str) -> TestFileResult:
    path_str = str(xml_path)
    try:
        dom = parse(path_str)
    except ExpatError as e:
        raise RuntimeError(f"Failed to parse {path_str}: {e}")

    # testsuites / testsuite 노드 찾기
    suites = dom.getElementsByTagName("testsuites") or dom.getElementsByTagName("testsuite")
    if not suites:
        raise RuntimeError(f"No <testsuites> or <testsuite> in {path_str}")
    root = suites[0]

    # timestamp 수집: 'timestamp' 및 'timestamps' 속성 모두 체크
    timestamps: list[datetime] = []
    def collect_ts(node):
        for attr in ("timestamp", "timestamps"):
            if node.hasAttribute(attr):
                s = node.getAttribute(attr)
                # ISO 형식 끝에 Z 있으면 제거
                if s.endswith("Z"):
                    s = s[:-1]
                try:
                    timestamps.append(datetime.fromisoformat(s))
                except ValueError:
                    pass

    collect_ts(root)
    suite_nodes = (
        root.getElementsByTagName("testsuite")
        if root.tagName == "testsuites"
        else [root]
    )
    for suite in suite_nodes:
        collect_ts(suite)

    # failures, duration 집계
    failures_count = sum(int(n.getAttribute("failures") or 0) for n in suite_nodes)
    total_time     = sum(float(n.getAttribute("time") or 0.0) for n in suite_nodes)

    testcases     = dom.getElementsByTagName("testcase")
    skipped_count = 0
    cases: list[TestCaseResult] = []
    for tc in testcases:
        fullname = f"{tc.getAttribute('classname')}.{tc.getAttribute('name')}"
        elapsed  = float(tc.getAttribute("time") or 0.0)

        failure_nodes = tc.getElementsByTagName("failure")
        if failure_nodes:
            status = 'failed'
            node   = failure_nodes[0]
            msg    = node.getAttribute("message") or ""
            text   = node.firstChild.nodeValue if node.firstChild else ""
            failure_message = (msg + "\n" + text).strip()
        elif tc.getElementsByTagName("skipped"):
            status = 'skipped'
            skipped_count += 1
            failure_message = ""
        else:
            status = 'success'
            failure_message = ""

        cases.append(TestCaseResult(fullname, elapsed, status, failure_message))

    earliest = min(timestamps) if timestamps else None
    filename = Path(path_str).name
    return TestFileResult(
        filename=filename,
        total=len(testcases),
        failures=failures_count,
        skipped=skipped_count,
        duration=total_time,
        timestamp=earliest,
        cases=cases
    )

def parse_files(xml_paths: list[Path] | list[str]):
    results = []
    tot = fail = skip = 0
    all_ts: list[datetime] = []
    for p in xml_paths:
        res = parse_file(p)
        results.append(res)
        tot += res.total
        fail += res.failures
        skip += res.skipped
        if res.timestamp:
            all_ts.append(res.timestamp)
    return results, tot, fail, skip, all_ts
