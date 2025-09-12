#!/usr/bin/env python3
"""
Fix script to add missing detail sections to HTML reports when XML links exist
This ensures all href="#detail_xxx.xml" links have corresponding id="detail_xxx.xml" sections
Compatible with gtest_report generated HTML files
"""

import xml.etree.ElementTree as ET
from pathlib import Path
import html
import re
import sys

def parse_xml_file(xml_path):
    """Parse XML file and extract test case information"""
    test_cases = []
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        # Parse GTest XML format
        for testsuite in root.findall('.//testsuite'):
            for testcase in testsuite.findall('testcase'):
                suite_name = testsuite.get('name', '')
                case_name = testcase.get('name', '')
                
                # Determine status
                if testcase.find('failure') is not None:
                    status = 'failed'
                elif testcase.find('skipped') is not None or testcase.get('status') == 'notrun':
                    status = 'skipped'
                else:
                    status = 'passed'
                
                test_cases.append({
                    'suite': suite_name,
                    'case': case_name,
                    'status': status
                })
    except Exception as e:
        print(f"Error parsing {xml_path}: {e}")
    
    return test_cases

def get_icon_html(status):
    """Return icon HTML based on status"""
    if status == 'passed':
        return '<span style="color: green;">✓</span>'
    elif status == 'failed':
        return '<span style="color: red;">✗</span>'
    else:  # skipped
        return '<span style="color: gray;">○</span>'

def generate_detail_section(xml_filename, test_cases):
    """Generate detail section HTML for XML file"""
    html_parts = []
    
    # Add header
    html_parts.append(f'<h3 id="detail_{xml_filename}">{xml_filename}</h3>')
    
    # Start table
    html_parts.append('''<table style="width: 100%; border-collapse: collapse; margin: 10px 0;">
  <colgroup>
    <col style="width:35%;">
    <col style="width:55%;">
    <col style="width:10%;">
  </colgroup>
  <tr style="background: #f2f2f2;">
    <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Test Suite</th>
    <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Test Case</th>
    <th style="border: 1px solid #ddd; padding: 8px; text-align: center;">Result</th>
  </tr>''')
    
    # Add test cases
    for case in test_cases:
        suite = html.escape(case['suite'])
        case_name = html.escape(case['case'])
        icon = get_icon_html(case['status'])
        
        html_parts.append(f'''  <tr>
    <td style="border: 1px solid #ddd; padding: 8px;">{suite}</td>
    <td style="border: 1px solid #ddd; padding: 8px;">{case_name}</td>
    <td style="border: 1px solid #ddd; padding: 8px; text-align: center;">{icon}</td>
  </tr>''')
    
    # End table
    html_parts.append('</table>')
    
    return '\n'.join(html_parts)

def extract_xml_files_from_html(html_content):
    """Extract referenced XML filenames from HTML content"""
    # Find href='#detail_xxx.xml' patterns
    pattern = r"href='#detail_([^']+\.xml)'"
    matches = re.findall(pattern, html_content)
    return list(set(matches))  # Remove duplicates

def fix_report(report_path, xml_dir):
    """Fix a single report file"""
    report_name = report_path.name
    
    # Read HTML file
    with open(report_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Check if detail sections already exist
    if 'id="detail_' in html_content:
        print(f"  ⏭️  {report_name}: Already has detail sections")
        return False
    
    # Extract referenced XML files from HTML
    xml_files = extract_xml_files_from_html(html_content)
    
    if not xml_files:
        print(f"  ⚠️  {report_name}: No XML references found")
        return False
    
    # Generate detail sections for each XML file
    detail_sections = []
    
    # Add Detailed Test Results header
    detail_sections.append('\n\n<h2>Detailed Test Results</h2>')
    
    added_count = 0
    for xml_file in sorted(xml_files):
        xml_path = xml_dir / xml_file
        if xml_path.exists():
            test_cases = parse_xml_file(xml_path)
            if test_cases:
                detail_section = generate_detail_section(xml_file, test_cases)
                detail_sections.append(detail_section)
                added_count += 1
                print(f"    - {xml_file}: {len(test_cases)} test cases added")
        else:
            print(f"    - {xml_file}: File not found")
    
    if added_count == 0:
        print(f"  ⚠️  {report_name}: No XML files found")
        return False
    
    # Insert detail sections before </body> tag
    if '</body>' in html_content:
        html_content = html_content.replace('</body>', '\n'.join(detail_sections) + '\n</body>')
    else:
        # If no </body> tag, append to end
        html_content += '\n'.join(detail_sections)
    
    # Save modified HTML
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"  ✅ {report_name}: {added_count} XML detail sections added")
    return True

def main():
    """Main function to fix all report files"""
    if len(sys.argv) > 1:
        # Use provided paths
        report_dir = Path(sys.argv[1])
        xml_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else report_dir.parent
    else:
        # Default paths for PARA project
        report_dir = Path('/home/popcornsar/DevOps/01_Jenkins/jenkins_home/workspace/PARA-918/test-results/html_report')
        xml_dir = Path('/home/popcornsar/DevOps/01_Jenkins/jenkins_home/workspace/PARA-918/test-results')
    
    # Report files to fix
    report_files = [
        'SCIT_Report.html',
        'SCT_Report.html', 
        'SRT_Report.html',
        'UIT_Report.html',
        'UT_Report.html'
    ]
    
    print("🔧 Fixing test report detail sections...")
    print(f"📂 Report directory: {report_dir}")
    print(f"📂 XML directory: {xml_dir}")
    print("")
    
    success_count = 0
    for report_file in report_files:
        report_path = report_dir / report_file
        if report_path.exists():
            print(f"📄 Processing {report_file}...")
            if fix_report(report_path, xml_dir):
                success_count += 1
        else:
            # Try to find any HTML files with similar pattern
            similar_files = list(report_dir.glob(f"*{report_file.split('_')[0]}*.html"))
            if similar_files:
                for similar_file in similar_files:
                    print(f"📄 Processing {similar_file.name}...")
                    if fix_report(similar_file, xml_dir):
                        success_count += 1
            else:
                print(f"  ❌ {report_file}: File not found")
    
    print("")
    print(f"✨ Completed: {success_count} files fixed")

if __name__ == '__main__':
    main()