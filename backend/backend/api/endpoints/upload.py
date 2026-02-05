from pathlib import Path
import shutil
import uuid
from typing import Dict

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import pytesseract
from PIL import Image

from backend.config import settings

router = APIRouter()

UPLOAD_DIR = Path("backend/static/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

@router.post("/upload", summary="Upload Image for OCR", description="Uploads an image, saves it, and extracts text using OCR.")
async def upload_image(file: UploadFile = File(...)) -> Dict[str, str]:
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    # Generate unique filename
    file_ext = Path(file.filename).suffix
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = UPLOAD_DIR / unique_filename

    # Save file
    try:
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    # Construct public URL (assuming /static mount)
    # In production, this heavily depends on reverse proxy setup, 
    # but for local dev with StaticFiles mount, this works.
    image_url = f"/static/uploads/{unique_filename}"

    # Perform OCR
    extracted_text = ""
    try:
        image = Image.open(file_path)
        extracted_text = pytesseract.image_to_string(image, lang="chi_sim+eng")
    except Exception as e:
        # Fallback if tesseract is not installed or fails
        print(f"OCR Failed: {str(e)}")
        # We don't fail the upload, just return empty text
        pass

    return {
        "url": image_url,
        "text": extracted_text.strip()
    }
