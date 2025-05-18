from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from google import genai
from app.api.pdf_upload import db, embed_fn
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

router = APIRouter()

class Query(BaseModel):
    query: str

@router.post("/")
async def chat(query: Query):
    if not query.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    try:
        # Switch embedding function to query mode
        embed_fn.document_mode = False
        
        # Get relevant documents
        results = db.query(
            query_texts=[query.query],
            n_results=3,
            include=["documents", "metadatas"]
        )
        
        # Switch back to document mode
        embed_fn.document_mode = True
        
        if not results["documents"][0]:
            return {"answer": "No relevant information found in the documents."}
        
        # Prepare context from retrieved documents
        context = "\n\n".join(results["documents"][0])
        sources = [meta["source"] for meta in results["metadatas"][0]]
        
        # Prepare prompt
        prompt = f"""Answer the following question based on the provided context. If the context doesn't contain relevant information, say so.

Context: {context}

Question: {query.query}"""
        
        # Generate response using Gemini
        client = genai.Client()
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        
        return {
            "answer": response.text,
            "sources": sources
        }
    
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
