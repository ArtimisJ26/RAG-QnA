from setuptools import setup, find_packages

setup(
    name="rag-qna",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "fastapi",
        "uvicorn",
        "langchain",
        "langchain-community",
        "chromadb",
        "PyMuPDF",
        "python-multipart",
        "pydantic",
        "scikit-learn",
        "numpy",
    ],
) 