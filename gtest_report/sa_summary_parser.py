from xml.dom.minidom import parse
from collections import defaultdict
from pathlib import Path
import re

def parse_sa_file_enhanced(report_xml_path: Path, debug: bool = False):
    dom = parse(str(report_xml_path))
    messages = dom.getElementsByTagName("message")

    comp_counts = defaultdict(int)
    comp_files = defaultdict(set)
    severity_counts = defaultdict(int)
    ruleid_counts = defaultdict(int)
    etc_files = []

    ruleid_pattern = re.compile(r"\[AUTOSAR Rule ([^\]]+)\]")

    for msg in messages:
        file_node = msg.getElementsByTagName("file")
        if not file_node or file_node[0].firstChild is None:
            continue
        file_path = file_node[0].firstChild.nodeValue.strip()
        parts = Path(file_path).parts
        component = "etc"
        try:
            idx = parts.index("para-api")
            if idx + 1 < len(parts):
                component = parts[idx + 1]
        except ValueError:
            pass

        comp_counts[component] += 1
        comp_files[component].add(file_path)

        type_node = msg.getElementsByTagName("type")
        severity = type_node[0].firstChild.nodeValue.strip() if type_node and type_node[0].firstChild else "Unknown"
        severity_counts[severity] += 1

        desc_node = msg.getElementsByTagName("desc")
        desc_text = desc_node[0].firstChild.nodeValue.strip() if desc_node and desc_node[0].firstChild else ""
        m = ruleid_pattern.search(desc_text)
        ruleid = m.group(1) if m else "etc"
        ruleid_counts[ruleid] += 1

        if component == "etc":
            etc_files.append(file_path)

    if debug and etc_files:
        with open("etc.txt", "w", encoding="utf-8") as f:
            for fp in etc_files:
                f.write(fp + "\n")

    return {
        "total_components": len(comp_counts),
        "total_files": sum(len(v) for v in comp_files.values()),
        "comp_files_count": {k: len(v) for k, v in comp_files.items()},
        "total_violations": sum(comp_counts.values()),
        "comp_counts": dict(comp_counts),
        "severity_counts": dict(severity_counts),
        "ruleid_counts": dict(ruleid_counts),
    }