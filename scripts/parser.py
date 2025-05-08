# scripts/parser.py
"""
Parses Google Test XML files into structured Python objects.
"""
import os
from xml.dom.minidom import parse
from xml.parsers.expat import ExpatError
from datetime import datetime

class TestCaseResult:
    def __init__(self, name: str, time: float, status: str):
        self.name = name
        self.time = time
        self.status = status  # 'success', 'failed', or 'skipped'

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
    suites = dom.getElementsByTagName("testsuites") \
             or dom.getElementsByTagName("testsuite")
    if not suites:
        raise RuntimeError(f"No <testsuites> or <testsuite> in {xml_path}")
    root = suites[0]

    # collect timestamps
    timestamps: list[datetime] = []
    def add_ts(node):
        # look for both "timestamp" and (legacy) "timestamps"
        for attr in ("timestamp", "timestamps"):
            if node.hasAttribute(attr):
                s = node.getAttribute(attr)
                # strip trailing 'Z'
                if s.endswith("Z"):
                    s = s[:-1]
                try:
                    # original format was YYYY-MM-DDTHH:MM:SS
                    dt = datetime.fromisoformat(s)
                    timestamps.append(dt)
                except ValueError:
                    pass
    # root
    add_ts(root)
    # any nested <testsuite>
    nodes = (root.getElementsByTagName("testsuite")
             if root.tagName == "testsuites" else [root])
    for suite in nodes:
        add_ts(suite)

    # failures & total_time
    failures = sum(int(n.getAttribute("failures") or 0) for n in nodes)
    total_time = sum(float(n.getAttribute("time") or 0.0) for n in nodes)

    # per-test-case results
    testcases = dom.getElementsByTagName("testcase")
    skipped_count = 0
    cases: list[TestCaseResult] = []
    for tc in testcases:
        fullname = f"{tc.getAttribute('classname')}.{tc.getAttribute('name')}"
        elapsed = float(tc.getAttribute("time") or 0.0)
        if tc.getElementsByTagName("skipped"):
            status = 'skipped'
            skipped_count += 1
        elif tc.getElementsByTagName("failure"):
            status = 'failed'
        else:
            status = 'success'
        cases.append(TestCaseResult(fullname, elapsed, status))

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
