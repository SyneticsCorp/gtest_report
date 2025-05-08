"""
Command-line interface for the GTest HTML report generator.
"""
#!/usr/bin/env python3
import os
import sys
# Ensure local modules are in path
sys.path.insert(0, os.path.dirname(__file__))

import argparse
import glob
from generator import generate_report


def main():
    parser = argparse.ArgumentParser(
        description='Generate HTML report from Google Test XML files.'
    )
    parser.add_argument('project', help='Project name')
    parser.add_argument('report', help='Report name')
    parser.add_argument('output', help='Output HTML path')
    parser.add_argument('inputs', nargs='+', help='Input XML file or glob patterns')
    args = parser.parse_args()

    xml_files: list[str] = []
    for pattern in args.inputs:
        xml_files.extend(glob.glob(pattern))
    if not xml_files:
        print('Error: No XML files found for patterns', args.inputs, file=sys.stderr)
        sys.exit(1)

    generate_report(args.project, args.report, xml_files, args.output)


if __name__ == '__main__':
    main()
