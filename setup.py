# File: setup.py

from setuptools import setup, find_packages

setup(
    name="gtest_report",
    version="1.0.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "Jinja2>=3.0",
    ],
    entry_points={
        "console_scripts": [
            "gtest-report = gtest_report.cli:main",
        ],
    },
    package_data={
        "gtest_report": [
            "templates/*.html",
            "html_resources/*.*",
        ],
    },
)
