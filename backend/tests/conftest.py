import os
import sys
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import numpy as np
import shutil

# Add the backend directory to Python path
backend_dir = str(Path(__file__).parent.parent)
sys.path.append(backend_dir)

# Test constants
TEST_DATA_DIR = Path(__file__).parent / "test_data"
TEST_EMBEDDING_DIM = 768

# Load test environment variables
os.environ["GOOGLE_API_KEY"] = "test_key_for_testing"
os.environ["ENVIRONMENT"] = "test"

# Import after setting environment variables
from app.api.pdf_upload import db, GeminiEmbeddingFunction

class MockEmbeddingResponse:
    def __init__(self, embedding):
        self.embedding = embedding

class MockGenerateResponse:
    def __init__(self, text):
        self.text = text

class MockGeminiClient:
    def __init__(self):
        self.models = MagicMock()
        self.models.embed_content.return_value = MockEmbeddingResponse(np.ones(TEST_EMBEDDING_DIM))
        
        def generate_content_mock(*args, **kwargs):
            # Extract query from kwargs
            prompt = kwargs.get('contents', '')
            if isinstance(prompt, list):
                prompt = ' '.join(str(p) for p in prompt)
            
            # Return contextual responses
            if "test content" in prompt.lower():
                return MockGenerateResponse("This document contains test content for RAG testing.")
            elif "sample document" in prompt.lower():
                return MockGenerateResponse("This is a sample document used for testing.")
            elif "chunking" in prompt.lower():
                return MockGenerateResponse("The document discusses chunking and embedding techniques.")
            else:
                return MockGenerateResponse("This document appears to be about testing RAG functionality with various content types.")
        
        self.models.generate_content = generate_content_mock

class MockEmbeddingFunction:
    def __init__(self):
        self.document_mode = True
        self.client = MockGeminiClient()
        # Create deterministic but different embeddings for different content
        self.content_embeddings = {
            "test content": np.ones(TEST_EMBEDDING_DIM),
            "sample document": np.ones(TEST_EMBEDDING_DIM) * 0.5,
            "chunking and embedding": np.ones(TEST_EMBEDDING_DIM) * 0.8
        }
    
    def __call__(self, input):
        if isinstance(input, str):
            # Return content-specific embedding if available
            for content, embedding in self.content_embeddings.items():
                if content.lower() in input.lower():
                    return [embedding.tolist()]
            return [np.ones(TEST_EMBEDDING_DIM).tolist()]
        return [self.__call__(text)[0] for text in input]

@pytest.fixture(scope="session", autouse=True)
def test_env_setup():
    """Set up test environment"""
    # Create test data directory
    TEST_DATA_DIR.mkdir(exist_ok=True)
    yield
    # Cleanup after all tests
    shutil.rmtree(TEST_DATA_DIR, ignore_errors=True)

@pytest.fixture(scope="session")
def mock_gemini():
    """Mock both embedding and text generation"""
    with patch('google.genai.Client', return_value=MockGeminiClient()) as client_mock:
        with patch('app.api.pdf_upload.GeminiEmbeddingFunction.__call__', new_callable=MockEmbeddingFunction) as embed_mock:
            yield (embed_mock, client_mock)

@pytest.fixture(scope="session")
def test_db():
    """Provide a test database instance"""
    return db

@pytest.fixture(scope="function")
def clean_db(test_db):
    """Clean the database before and after each test"""
    try:
        results = test_db.get()
        if results and results['ids']:
            test_db.delete(ids=results['ids'])
    except Exception:
        pass
    
    yield test_db
    
    try:
        results = test_db.get()
        if results and results['ids']:
            test_db.delete(ids=results['ids'])
    except Exception:
        pass 