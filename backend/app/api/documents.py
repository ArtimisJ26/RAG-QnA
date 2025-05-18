from fastapi import APIRouter, HTTPException
from app.api.pdf_upload import db

router = APIRouter()


@router.delete("/{document_name}")
async def delete_document(document_name: str):
    try:
        # Get all documents
        results = db.get()
        
        if not results or len(results["ids"]) == 0:
            raise HTTPException(
                status_code=404,
                detail=f"Document '{document_name}' not found"
            )
        
        # Find all chunks that belong to this document
        chunk_ids = []
        for idx, metadata in enumerate(results["metadatas"]):
            source = metadata.get("source", "")
            if source.startswith(document_name + " (Page"):
                chunk_ids.append(results["ids"][idx])
        
        if not chunk_ids:
            raise HTTPException(
                status_code=404,
                detail=f"Document '{document_name}' not found"
            )
        
        # Delete all chunks associated with this document
        db.delete(
            ids=chunk_ids
        )
        
        return {"message": f"Document '{document_name}' successfully deleted"}
        
    except HTTPException:
        # Re-raise HTTP exceptions without wrapping them
        raise
    except Exception as e:
        logger.error(f"Error deleting document: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting document: {str(e)}"
        )
