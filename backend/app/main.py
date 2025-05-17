from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import chat, pdf_upload

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend dev URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix="/api/chat")
app.include_router(pdf_upload.router, prefix="/api/upload")

@app.get("/")
def read_root():
    return {"message": "Backend is running"}
