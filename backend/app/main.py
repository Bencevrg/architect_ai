from __future__ import annotations

from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.dxf_generator import generate_dxf_from_structure
from app.image_pipeline import process_image_to_structure
from app.llm_client import generate_or_modify_structure
from app.schemas import BuildingStructure

load_dotenv()

app = FastAPI(title="Architect AI Backend")


class GeneratePayload(BaseModel):
    prompt: str
    current_structure: Optional[dict] = None


# --- CORS beállítás (Frontend kommunikációhoz) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # vagy frontend URL pl. "http://localhost:8501"
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Alap endpoint az egész backendhez ---
@app.get("/")
async def root():
    return {"message": "Architect AI Backend fut"}


# --- Szöveges prompt alapján DXF generálás / módosítás ---
@app.post("/generate-or-modify-dxf")
async def generate_or_modify_dxf(payload: GeneratePayload):
    """
    payload: {
        "prompt": str,
        "current_structure": dict (opcionális)
    }
    """
    prompt = payload.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt megadása kötelező!")

    current_structure = payload.current_structure
    try:
        # AI generálás / módosítás JSON tervből
        updated_structure = generate_or_modify_structure(prompt, current_structure)
        validated = BuildingStructure.model_validate(updated_structure).model_dump()

        # DXF generálás
        output_file = generate_dxf_from_structure(validated)

        return {
            "structure": validated,
            "file": output_file
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Kép alapján struktúra generálása ---
@app.post("/image-to-dxf")
async def image_to_dxf(file: UploadFile = File(...)):
    """
    PNG képet vár, OCR + AI pipeline feldolgozza.
    Visszaadja a generált JSON tervrajzot.
    """
    if not file.filename.lower().endswith(".png"):
        raise HTTPException(status_code=400, detail="Csak PNG képfájl elfogadott.")

    try:
        # Kép feldolgozása OCR + AI pipeline segítségével
        structure = await process_image_to_structure(file)
        validated = BuildingStructure.model_validate(structure).model_dump()
        return {"structure": validated}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Kép feldolgozási hiba: {e}")
