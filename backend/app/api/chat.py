<<<<<<< HEAD
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from api.pdf_upload import db, GeminiEmbeddingFunction
import chromadb

router = APIRouter()

# ChromaDB client and collection
embed_fn = GeminiEmbeddingFunction()
embed_fn.document_mode = False
chroma_client = chromadb.Client()
db = chroma_client.get_or_create_collection(name="document_db", embedding_function=embed_fn)

class ChatRequest(BaseModel):
    query: str

@router.post("/")
async def chat(req: ChatRequest):
    query = req.query.strip()
    
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    # Step 2 : Retrieve relevant chunks
    try:
        results = db.query(query_texts=[query], n_results=3)
        relevant_chunks = results["documents"][0]
        sources = results["metadatas"][0]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Retrieval failed: {str(e)}")
    
    # STEP 3: Generate final answer using Gemini
    try:
        # Combine chunks into context string
        docs = results["documents"][0]
        context = "\n\n".join([doc for doc in docs])

        prompt = f"""
        You are a helpful assistant. Use the following document excerpts to answer the question.

        Document context:
        {context}

        Question: {query}
        """

        # Use Gemini Pro for text generation        
        response = embed_fn.client.models.generate_content(
            model="gemini-2.0-flash",  # Using Gemini's fast model
            contents=prompt)  # The prompt with query and context

        answer = response.text

        return {"answer": answer}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating answer: {str(e)}")
=======
from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter()

class ChatRequest(BaseModel):
    question: str

@router.post("/")
async def chat(req: ChatRequest):
    return {"answer": f"You asked: {req.question}"}
>>>>>>> origin/main
