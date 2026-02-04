from setuptools import setup, find_packages

setup(
    name="proref",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "requests>=2.32.3",
        "numpy>=2.2.5",
        "python-dotenv>=1.1.0",
        "openai>=1.78.1",
        "SQLAlchemy>=2.0.41",
        "tiktoken>=0.9.0",
        "tqdm>=4.67.1",
        "httpx>=0.28.1",
        "pydantic>=2.11.4",
        "typer>=0.9.0",
        "streamlit>=1.30.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
        ],
        "export": [
            "openpyxl>=3.1.0",
        ],
        "anthropic": [
            "anthropic>=0.18.0",
        ],
        "google": [
            "google-generativeai>=0.4.0",
        ],
        "all": [
            "openpyxl>=3.1.0",
            "anthropic>=0.18.0",
            "google-generativeai>=0.4.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "proref=app.cli:main",
        ],
    },
    python_requires=">=3.8",
    author="ProRef Team",
    author_email="eherrada@gmail.com",
    description="Product Refinement Automation Assistant",
    long_description=open("README.md", "r", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/your-username/proref",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
