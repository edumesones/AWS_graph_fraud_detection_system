from setuptools import setup, find_packages

setup(
    name="fraud-detection-graphs",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "networkx==3.2",
        "pandas==2.1.0",
        "numpy==1.24.0",
        "faker==20.0.0",
        "python-louvain==0.16",
        "scipy==1.11.0",
        "scikit-learn==1.3.0",
        "plotly==5.17.0",
        "streamlit==1.28.0",
        "pyvis==0.3.2",
        "pytest==7.4.0",
        "pytest-cov==4.1.0",
    ],
    python_requires=">=3.9",
)
