# File: setup.py

from setuptools import setup, find_packages

setup(
    name="gtest_report",
    version="1.0.0",
    packages=find_packages(),         # gtest_report 패키지 포함
    include_package_data=True,        # MANIFEST.in 참조
    install_requires=[
        "Jinja2>=3.0",
        "matplotlib>=3.0",
    ],
    entry_points={
        'console_scripts': [
            'gtest-report = gtest_report.cli:main',
        ],
    },
    package_data={
        'gtest_report': [
            'templates/*.html',
            'html_resources/*.*',
        ],
    },
    author="Your Name",
    description="Automated GTest HTML Report Generator",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
)
