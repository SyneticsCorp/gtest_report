# File: scripts/parser.py
"""
Parses Google Test XML files into structured Python objects.
"""
import os
from xml.dom.minidom import parse
from xml.parsers.expat import ExpatError
from datetime import datetime

class TestCaseResult:
    def __init__(self, name: str, time: float, status: str, failure_message: str = ""):
        self.name = name
        self.time = time
        self.status = status        # 'success', 'failed', or 'skipped'
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

def parse_file(xml_path: str) -> TestFileResult:
    try:
        dom = parse(xml_path)
    except ExpatError as e:
        raise RuntimeError(f"Failed to parse {xml_path}: {e}")

    # root <testsuites> or <testsuite>
    suites = dom.getElementsByTagName("testsuites") or dom.getElementsByTagName("testsuite")
    if not suites:
        raise RuntimeError(f"No <testsuites> or <testsuite> in {xml_path}")
    root = suites[0]

    # collect timestamps
    timestamps: list[datetime] = []
    def add_ts(node):
        for attr in ("timestamp", "timestamps"):
            if node.hasAttribute(attr):
                s = node.getAttribute(attr)
                if s.endswith("Z"):
                    s = s[:-1]
                try:
                    dt = datetime.fromisoformat(s)
                    timestamps.append(dt)
                except ValueError:
                    pass
    add_ts(root)
    suite_nodes = root.getElementsByTagName("testsuite") if root.tagName=="testsuites" else [root]
    for suite in suite_nodes:
        add_ts(suite)

    # failures & total_time
    failures   = sum(int(n.getAttribute("failures") or 0)  for n in suite_nodes)
    total_time = sum(float(n.getAttribute("time") or 0.0) for n in suite_nodes)

    # parse testcases
    testcases = dom.getElementsByTagName("testcase")
    skipped_count = 0
    cases: list[TestCaseResult] = []
    for tc in testcases:
        fullname = f"{tc.getAttribute('classname')}.{tc.getAttribute('name')}"
        elapsed  = float(tc.getAttribute("time") or 0.0)

        # determine status & capture failure message
        failure_nodes = tc.getElementsByTagName("failure")
        if failure_nodes:
            status = 'failed'
            node   = failure_nodes[0]
            msg_attr = node.getAttribute("message") or ""
            # 안전하게 텍스트 노드 추출
            if node.firstChild and node.firstChild.nodeValue:
                msg_text = node.firstChild.nodeValue
            else:
                msg_text = ""
            failure_message = (msg_attr + "\n" + msg_text).strip()
        elif tc.getElementsByTagName("skipped"):
            status          = 'skipped'
            skipped_count  += 1
            failure_message = ""
        else:
            status          = 'success'
            failure_message = ""

        cases.append(TestCaseResult(fullname, elapsed, status, failure_message))

    earliest = min(timestamps) if timestamps else None
    return TestFileResult(
        filename=os.path.basename(xml_path),
        total=len(testcases),
        failures=failures,
        skipped=skipped_count,
        duration=total_time,
        timestamp=earliest,
        cases=cases,
    )

def parse_files(xml_paths: list[str]) -> tuple[list[TestFileResult], int, int, int, list[datetime]]:
    results = []
    tot = fails = skip = 0
    all_ts: list[datetime] = []
    for p in xml_paths:
        res = parse_file(p)
        results.append(res)
        tot   += res.total
        fails += res.failures
        skip  += res.skipped
        if res.timestamp:
            all_ts.append(res.timestamp)
    return results, tot, fails, skip, all_ts
