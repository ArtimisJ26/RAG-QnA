from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.api import chat, pdf_upload, documents
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

class CustomHeaderMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return response

app = FastAPI()

# Configure for larger file uploads
app.add_middleware(CustomHeaderMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend dev URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure maximum upload size to 50MB
app.state.max_upload_size = 50 * 1024 * 1024  # 50MB in bytes

# Remove trailing slashes
app.router.redirect_slashes = False

app.include_router(chat.router, prefix="/api/chat")
app.include_router(pdf_upload.router, prefix="/api/upload")
app.include_router(documents.router, prefix="/api/documents")

@app.get("/")
def read_root():
    return {"message": "Backend is running"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}
