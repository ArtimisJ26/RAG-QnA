<<<<<<< HEAD
import os
import glob
from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import List
import chromadb
import PyPDF2
from dotenv import load_dotenv
from google import genai
import uuid


router = APIRouter()

# Load environment variables
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")


# Custom embedding function for ChromaDB
class GeminiEmbeddingFunction:
    def __init__(self):
        self.client = genai.Client(api_key=GOOGLE_API_KEY)
        self.document_mode = True
        
    def __call__(self, input):
        embedding_task = "retrieval_document" if self.document_mode else "retrieval_query"
        response = self.client.models.embed_content(
            model="models/text-embedding-004",
            contents=input,
            config={"task_type": embedding_task},
        )
        return [e.values for e in response.embeddings]


# Create ChromaDB client and collection
chroma_client = chromadb.Client()
embed_fn = GeminiEmbeddingFunction()
db = chroma_client.get_or_create_collection(name="document_db", embedding_function=embed_fn)



def chunk_text(text, max_length=500, overlap=50):
    """
    Splits text into chunks with optional overlap.
    """
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = words[i:i + max_length]
        chunks.append(' '.join(chunk))
        i += max_length - overlap
    return chunks




# Define a POST endpoint /api/upload/ that accepts a PDF file.
@router.post("/")
async def upload_pdf(file: UploadFile = File(...)):
    # Validate that the uploaded file ends in .pdf.
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    # Writes the uploaded file to a temporary location on disk.
    temp_path = f"./temp_{file.filename}"
    with open(temp_path, "wb") as buffer:
        buffer.write(await file.read())


    try:

        documents, document_sources = [], []

        # Open the uploaded PDF file.
        with open(temp_path, 'rb') as pdf_file:
            pdf_reader = PyPDF2.PdfReader(pdf_file, strict=False)
            filename = file.filename

            # Loop through each page.
            for page_num, page in enumerate(pdf_reader.pages):
                # Extract and clean the text.
                text = page.extract_text()
                if text and not text.isspace():
                    chunks = chunk_text(text)
                    documents.extend(chunks)
                    # Store that text in a list (to prepare for chunking + embedding later).
                    document_sources.extend([f"{filename} (Page {page_num+1}, Chunk {i+1})" for i in range(len(chunks))])
        
        # Add to vector database
        if documents:
            db.add(
                documents=documents,
                ids=[str(uuid.uuid4()) for _ in documents],
                metadatas=[{"source": source} for source in document_sources]
            )
        
        # Clean up temp file
        os.remove(temp_path)
        
        return {
            "filename": file.filename,
            "pages_processed": len(documents),
            "total_documents": db.count()
            # "extracted_pages": documents    # For checking generated chunks of documents
        }

    except Exception as e:
        # Clean up on error
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")

=======
from fastapi import APIRouter, UploadFile, File

router = APIRouter()

@router.post("/")
async def upload_pdf(file: UploadFile = File(...)):
    return {"filename": file.filename}
>>>>>>> origin/main
