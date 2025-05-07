from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter()

class ChatRequest(BaseModel):
    question: str

@router.post("/")
async def chat(req: ChatRequest):
    return {"answer": f"You asked: {req.question}"}
