from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="mcp-protocol-validator",
    version="1.0.0",
    author="Scott Wilcox",
    author_email="example@example.com",  # Replace with actual email
    description="Testing framework and reference implementations for the Model Conversation Protocol (MCP)",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/scottwilcox/mcp-protocol-validator",
    project_urls={
        "Bug Tracker": "https://github.com/scottwilcox/mcp-protocol-validator/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU Affero General Public License v3",
        "Operating System :: OS Independent",
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Testing",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
    ],
    packages=find_packages(include=["mcp_testing", "mcp_testing.*", "minimal_mcp_server", "minimal_http_server"]),
    include_package_data=True,
    python_requires=">=3.9",
    install_requires=[
        "jinja2>=3.0.0",
        "requests>=2.25.0",
        "aiohttp>=3.8.0",
        "jsonschema>=4.0.0",
    ],
    entry_points={
        "console_scripts": [
            "mcp-compliance-report=mcp_testing.scripts.compliance_report:main",
            "mcp-http-test=mcp_testing.scripts.http_test:main",
            "mcp-basic-interaction=mcp_testing.scripts.basic_interaction:main",
            "mcp-minimal-server=minimal_mcp_server.minimal_mcp_server:main",
            "mcp-minimal-http-server=minimal_http_server.minimal_http_server:main",
        ],
    },
) 