from setuptools import setup, find_packages

setup(
    name="perf-framework",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "locust>=2.0.0",
        "jinja2>=3.0.0",
        "pyyaml>=6.0",
        "requests>=2.28.0",
        "plotly>=5.0.0",
    ],
    entry_points={
        "console_scripts": [
            "perf-framework=perf_framework.cli:main",
        ],
    },
    python_requires=">=3.9",
)
