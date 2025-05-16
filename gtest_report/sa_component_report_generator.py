from collections import defaultdict
from xml.dom.minidom import parse
from pathlib import Path
import re

def generate_sa_component_reports(report_xml_path: Path, output_dir: Path):
    ruleid_pattern = re.compile(r"\[AUTOSAR Rule ([^\]]+)\]")
    dom = parse(str(report_xml_path))
    messages = dom.getElementsByTagName("message")

    components = defaultdict(lambda: {
        "violations": 0,
        "severity_counts": defaultdict(int),
        "ruleid_counts": defaultdict(int),
        "file_counts": defaultdict(int),
        "file_violations": defaultdict(list),
    })

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

        type_node = msg.getElementsByTagName("type")
        severity = type_node[0].firstChild.nodeValue.strip() if type_node and type_node[0].firstChild else "Unknown"

        desc_node = msg.getElementsByTagName("desc")
        ruleid = "etc"
        desc_text = desc_node[0].firstChild.nodeValue.strip() if desc_node and desc_node[0].firstChild else ""
        m = ruleid_pattern.search(desc_text)
        if m:
            ruleid = m.group(1)

        line_node = msg.getElementsByTagName("line")
        line = line_node[0].firstChild.nodeValue.strip() if line_node and line_node[0].firstChild else ""

        violation_text = desc_text

        comp_data = components[component]
        comp_data["violations"] += 1
        comp_data["severity_counts"][severity] += 1
        comp_data["ruleid_counts"][ruleid] += 1
        comp_data["file_counts"][file_path] += 1
        comp_data["file_violations"][file_path].append({
            "line": line,
            "ruleid": ruleid,
            "severity": severity,
            "desc": violation_text,
        })

    from jinja2 import Environment, FileSystemLoader, select_autoescape
    tpl_dir = Path(__file__).parent / "templates"
    env = Environment(
        loader=FileSystemLoader(str(tpl_dir)),
        autoescape=select_autoescape(["html"]),
    )
    template = env.get_template("sa_component_report.html")

    for comp, data in components.items():
        output_file = output_dir / f"SA_Report_{comp}.html"
        html = template.render(
            component=comp,
            total_violations=data["violations"],
            severity_counts=data["severity_counts"],
            ruleid_counts=data["ruleid_counts"],
            file_counts=data["file_counts"],
            file_violations=data["file_violations"],
        )
        output_file.write_text(html, encoding="utf-8")
