from fastapi import APIRouter, UploadFile, File

router = APIRouter()

@router.post("/")
async def upload_pdf(file: UploadFile = File(...)):
    return {"filename": file.filename}
