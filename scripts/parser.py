# File: scripts/parser.py
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
        self.filename = filename
        self.total = total
        self.failures = failures
        self.skipped = skipped
        self.duration = duration
        self.timestamp = timestamp
        self.cases = cases

def parse_file(xml_path: str) -> TestFileResult:
    """
    Parse a single Google Test XML file and return a TestFileResult.
    """
    try:
        dom = parse(xml_path)
    except ExpatError as e:
        raise RuntimeError(f"Failed to parse {xml_path}: {e}")

    # Identify root <testsuites> or <testsuite>
    suites = dom.getElementsByTagName("testsuites") or dom.getElementsByTagName("testsuite")
    if not suites:
        raise RuntimeError(f"No <testsuites> or <testsuite> in {xml_path}")
    root = suites[0]
    suite_nodes = (
        root.getElementsByTagName("testsuite")
        if root.tagName == "testsuites"
        else [root]
    )

    failures = 0
    total_time = 0.0
    skipped_count = 0
    timestamps: list[datetime] = []

    def add_timestamp(node):
        if node.hasAttribute("timestamp"):
            try:
                ts = datetime.fromisoformat(node.getAttribute("timestamp"))
                timestamps.append(ts)
            except ValueError:
                pass

    add_timestamp(root)
    for suite in suite_nodes:
        failures += int(suite.getAttribute("failures") or 0)
        total_time += float(suite.getAttribute("time") or 0.0)
        add_timestamp(suite)

    # Parse individual testcases
    testcases = dom.getElementsByTagName("testcase")
    cases: list[TestCaseResult] = []
    for tc in testcases:
        name = f"{tc.getAttribute('classname')}.{tc.getAttribute('name')}"
        elapsed = float(tc.getAttribute("time") or 0.0)
        if tc.getElementsByTagName("skipped"):
            status = 'skipped'
            skipped_count += 1
        elif tc.getElementsByTagName("failure"):
            status = 'failed'
        else:
            status = 'success'
        cases.append(TestCaseResult(name, elapsed, status))

    timestamp = min(timestamps) if timestamps else None
    return TestFileResult(
        filename=os.path.basename(xml_path),
        total=len(testcases),
        failures=failures,
        skipped=skipped_count,
        duration=total_time,
        timestamp=timestamp,
        cases=cases,
    )

def parse_files(xml_paths: list[str]) -> tuple[list[TestFileResult], int, int, int, list[datetime]]:
    """
    Parse multiple XML files and aggregate overall statistics.
    Returns:
      (list of TestFileResult, total_tests, total_failures, total_skipped, all_timestamps)
    """
    results: list[TestFileResult] = []
    total_tests = total_failures = total_skipped = 0
    all_timestamps: list[datetime] = []

    for path in xml_paths:
        result = parse_file(path)
        results.append(result)
        total_tests += result.total
        total_failures += result.failures
        total_skipped += result.skipped
        if result.timestamp:
            all_timestamps.append(result.timestamp)

    return results, total_tests, total_failures, total_skipped, all_timestamps
