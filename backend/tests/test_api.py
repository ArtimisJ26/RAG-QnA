import os
import pytest
from fastapi.testclient import TestClient
from app.main import app
import json
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from io import BytesIO
import asyncio
import pytest_asyncio
from concurrent.futures import ThreadPoolExecutor

client = TestClient(app)

# Test data directory
TEST_DATA_DIR = Path(__file__).parent / "test_data"
TEST_PDF = TEST_DATA_DIR / "sample.pdf"

@pytest.fixture(scope="session")
def sample_pdf():
    """Create a sample PDF with known content"""
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    
    # Add more substantial test content
    test_content = [
        ("Test content for RAG testing.", 750),
        ("This is a sample document.", 730),
        ("It contains multiple lines of text", 710),
        ("to test various aspects of the system.", 690),
        ("Including chunking and embedding.", 670),
    ]
    
    for text, y_pos in test_content:
        c.drawString(50, y_pos, text)
    c.save()
    
    # Write to file
    TEST_PDF.parent.mkdir(exist_ok=True)
    with open(TEST_PDF, "wb") as pdf_file:
        pdf_file.write(buffer.getvalue())
    
    return TEST_PDF

def test_health_check():
    """Test the health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_pdf_upload(clean_db, sample_pdf, mock_gemini):
    """Test PDF upload functionality"""
    # Test with valid PDF
    with open(sample_pdf, "rb") as pdf:
        response = client.post(
            "/api/upload",
            files={"file": ("test.pdf", pdf, "application/pdf")}
        )
        assert response.status_code == 200
        data = response.json()
        assert "filename" in data
        assert data["filename"] == "test.pdf"
        assert data["pages_processed"] == 1
        assert data["chunks_processed"] > 0

    # Test with invalid file type
    with open(sample_pdf, "rb") as pdf:
        response = client.post(
            "/api/upload",
            files={"file": ("test.txt", pdf, "text/plain")}
        )
        assert response.status_code == 400
        assert "detail" in response.json()

def test_chat_endpoint(clean_db, sample_pdf, mock_gemini):
    """Test the chat endpoint"""
    # Upload a document first
    with open(sample_pdf, "rb") as pdf:
        upload_response = client.post(
            "/api/upload",
            files={"file": ("test.pdf", pdf, "application/pdf")}
        )
        assert upload_response.status_code == 200

    # Test with valid query
    query = {"query": "What is this document about?"}
    response = client.post("/api/chat", json=query)
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "sources" in data
    assert len(data["sources"]) > 0
    assert "test.pdf" in data["sources"][0]
    
    # Verify response content
    assert "test content" in data["answer"].lower() or "sample document" in data["answer"].lower()

    # Test with empty query
    query = {"query": ""}
    response = client.post("/api/chat", json=query)
    assert response.status_code == 400
    assert "detail" in response.json()

def test_context_retrieval(clean_db, sample_pdf, mock_gemini):
    """Test context retrieval functionality"""
    # Upload a document first
    with open(sample_pdf, "rb") as pdf:
        upload_response = client.post(
            "/api/upload",
            files={"file": ("test.pdf", pdf, "application/pdf")}
        )
        assert upload_response.status_code == 200

    # Test specific content retrieval
    queries = [
        "test content",
        "sample document",
        "chunking and embedding"
    ]
    
    for query_text in queries:
        response = client.post("/api/chat", json={"query": query_text})
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "sources" in data
        assert len(data["sources"]) > 0
        # Check that sources are properly formatted
        for source in data["sources"]:
            assert "test.pdf" in source
            assert "Page" in source
            assert "Chunk" in source

def test_concurrent_uploads(clean_db, sample_pdf, mock_gemini):
    """Test concurrent PDF uploads"""
    num_concurrent = 3
    
    def upload_pdf():
        with open(sample_pdf, "rb") as pdf:
            return client.post(
                "/api/upload",
                files={"file": ("test.pdf", pdf, "application/pdf")}
            )
    
    # Run concurrent uploads
    with ThreadPoolExecutor(max_workers=num_concurrent) as executor:
        futures = [executor.submit(upload_pdf) for _ in range(num_concurrent)]
        responses = [future.result() for future in futures]
    
    # Verify all uploads succeeded
    for response in responses:
        assert response.status_code == 200
        data = response.json()
        assert data["pages_processed"] == 1
        assert data["chunks_processed"] > 0

def test_error_handling(clean_db):
    """Test error handling"""
    # Test missing file
    response = client.post("/api/upload", files={})
    assert response.status_code == 422  # FastAPI validation error
    assert "detail" in response.json()

    # Test invalid JSON
    response = client.post("/api/chat", json={"invalid": "query"})
    assert response.status_code == 422  # FastAPI validation error
    assert "detail" in response.json()

    # Test missing query parameter
    response = client.post("/api/chat", json={})
    assert response.status_code == 422  # FastAPI validation error
    assert "detail" in response.json()

    # Test malformed PDF
    TEST_DATA_DIR.mkdir(exist_ok=True)
    with open(TEST_DATA_DIR / "malformed.pdf", "wb") as f:
        f.write(b"This is not a PDF file")
    
    with open(TEST_DATA_DIR / "malformed.pdf", "rb") as f:
        response = client.post(
            "/api/upload",
            files={"file": ("malformed.pdf", f, "application/pdf")}
        )
        assert response.status_code == 400
        assert "Invalid PDF file" in response.json()["detail"] 