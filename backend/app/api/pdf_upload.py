import os
import glob
from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import List
import chromadb
from pypdf import PdfReader
from pypdf.errors import PdfStreamError
from dotenv import load_dotenv
from google import genai
import uuid
import logging
from io import BytesIO
from .embedding_status import init_embedding_status, update_embedding_status

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

router = APIRouter()

# Load environment variables
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    logger.warning("GOOGLE_API_KEY not found in environment variables")


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
@router.post("")
async def upload_pdf(file: UploadFile = File(...)):
    # Initialize embedding status
    init_embedding_status(file.filename)
    update_embedding_status(file.filename, 'processing', 0)

    try:
        # Get the maximum file size from app state
        max_size = 50 * 1024 * 1024  # 50MB default if not set in app state
        
        # Validate that the uploaded file ends in .pdf first
        if not file.filename.endswith('.pdf'):
            update_embedding_status(file.filename, 'error', 0, "Only PDF files are allowed")
            raise HTTPException(status_code=400, detail="Only PDF files are allowed")
        
        try:
            # Read file in chunks to avoid memory issues
            contents = bytearray()
            file_size = 0
            chunk_size = 1024 * 1024  # 1MB chunks
            
            while True:
                try:
                    chunk = await file.read(chunk_size)
                    if not chunk:
                        break
                    file_size += len(chunk)
                    if file_size > max_size:
                        update_embedding_status(file.filename, 'error', 0, "File too large")
                        raise HTTPException(
                            status_code=413,
                            detail=f"File too large. Maximum size allowed is 50MB"
                        )
                    contents.extend(chunk)
                except Exception as e:
                    logger.error(f"Error reading chunk: {str(e)}")
                    update_embedding_status(file.filename, 'error', 0, str(e))
                    raise HTTPException(
                        status_code=500,
                        detail="Error during file upload. Please try again."
                    )
            
            if file_size == 0:
                update_embedding_status(file.filename, 'error', 0, "Empty file uploaded")
                raise HTTPException(
                    status_code=400,
                    detail="Empty file uploaded"
                )
            
            # Create BytesIO object from contents
            pdf_stream = BytesIO(contents)
            
            try:
                # Try to read the PDF
                pdf_reader = PdfReader(pdf_stream)
                if len(pdf_reader.pages) == 0:
                    update_embedding_status(file.filename, 'error', 0, "PDF file contains no pages")
                    raise HTTPException(
                        status_code=400,
                        detail="PDF file contains no pages"
                    )
                
                documents = []
                document_sources = []
                
                # Update status to show PDF reading progress
                update_embedding_status(file.filename, 'processing', 10, "Reading PDF pages")
                
                # Process each page
                for page_num, page in enumerate(pdf_reader.pages):
                    try:
                        text = page.extract_text()
                        if text and not text.isspace():
                            # Chunk the text
                            chunks = chunk_text(text)
                            documents.extend(chunks)
                            document_sources.extend([
                                f"{file.filename} (Page {page_num+1}, Chunk {i+1})" 
                                for i in range(len(chunks))
                            ])
                            
                            # Update progress based on page processing (40% of total progress)
                            progress = 10 + int((page_num + 1) / len(pdf_reader.pages) * 40)
                            update_embedding_status(file.filename, 'processing', progress, "Processing PDF pages")
                            
                    except Exception as e:
                        logger.error(f"Error processing page {page_num + 1}: {str(e)}")
                        continue
                
                if not documents:
                    update_embedding_status(file.filename, 'error', 0, "No text content could be extracted")
                    raise HTTPException(
                        status_code=400,
                        detail="No text content could be extracted from PDF"
                    )
                
                # Add to vector database in smaller batches
                batch_size = 50  # Reduced batch size
                total_added = 0
                
                while total_added < len(documents):
                    batch_end = min(total_added + batch_size, len(documents))
                    batch_docs = documents[total_added:batch_end]
                    batch_sources = document_sources[total_added:batch_end]
                    
                    try:
                        db.add(
                            documents=batch_docs,
                            ids=[str(uuid.uuid4()) for _ in batch_docs],
                            metadatas=[{"source": source} for source in batch_sources]
                        )
                        
                        # Update progress based on embedding progress (50% of total progress)
                        progress = 50 + int((total_added + len(batch_docs)) / len(documents) * 50)
                        update_embedding_status(file.filename, 'processing', progress, "Creating embeddings")
                        
                    except Exception as e:
                        logger.error(f"Error adding batch to database: {str(e)}")
                        update_embedding_status(file.filename, 'error', progress, str(e))
                        raise HTTPException(
                            status_code=500,
                            detail=f"Database error: {str(e)}"
                        )
                    
                    total_added = batch_end
                
                # Update status to complete
                update_embedding_status(file.filename, 'complete', 100)
                
                return {
                    "filename": file.filename,
                    "pages_processed": len(pdf_reader.pages),
                    "chunks_processed": len(documents)
                }
                
            except PdfStreamError as e:
                logger.error(f"Error reading PDF: {str(e)}")
                update_embedding_status(file.filename, 'error', 0, str(e))
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid PDF file: {str(e)}"
                )
            except Exception as e:
                logger.error(f"Error processing PDF: {str(e)}")
                update_embedding_status(file.filename, 'error', 0, str(e))
                if "PDF" in str(e) or "pdf" in str(e):
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid PDF file: {str(e)}"
                    )
                raise HTTPException(
                    status_code=500,
                    detail=f"Error processing PDF: {str(e)}"
                )
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error processing upload: {str(e)}", exc_info=True)
            update_embedding_status(file.filename, 'error', 0, str(e))
            raise HTTPException(
                status_code=500,
                detail=str(e)
            )
    except Exception as e:
        # Ensure status is updated even if an unexpected error occurs
        update_embedding_status(file.filename, 'error', 0, str(e))
        raise
