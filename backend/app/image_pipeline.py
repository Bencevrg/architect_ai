"""Kép alapú struktúra generálás OCR + dummy LLM segítségével."""

from __future__ import annotations

import io
import shutil
from typing import Any, Dict

from PIL import Image

from app.llm_client import generate_or_modify_structure

try:  # pragma: no cover - Tesseract nem mindig elérhető
    import pytesseract  # type: ignore
except Exception:  # pragma: no cover - hiányzó függőség esetén
    pytesseract = None  # type: ignore

TESSERACT_AVAILABLE = bool(pytesseract and shutil.which("tesseract"))


async def process_image_to_structure(file) -> Dict[str, Any]:
    """
    Feldolgoz egy PNG képet és JSON struktúrát ad vissza:
    - szobák (rooms)
    - ajtók (doors)
    - ablakok (windows)
    - metadata (area, units)
    """

    # --- Kép betöltése ---
    image_bytes = await file.read()
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

    # --- OCR alkalmazása ---
    if TESSERACT_AVAILABLE:
        ocr_text = pytesseract.image_to_string(image)  # type: ignore[arg-type]
    else:
        ocr_text = ""

    # --- Alap JSON szerkezet a képről ---
    # Megjegyzés: az AI majd kiegészíti az adatokat pontos koordinátákkal
    initial_structure = {
        "rooms": [],
        "doors": [],
        "windows": [],
        "metadata": {"area": None, "units": "m"},
    }

    # --- OCR szöveg feldolgozása ---
    # Keresés szobanevek (R1, R2...) és méretek
    lines = ocr_text.splitlines()
    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Szoba felismerése
        if line.startswith("R"):
            name = line.split()[0]
            initial_structure["rooms"].append({
                "name": name,
                "points": []  # AI generálja a pontos koordinátákat
            })

        # Ajtó felismerés
        elif line.startswith("D"):
            initial_structure["doors"].append({
                "x": None,
                "y": None,
                "width": None,
                "angle": 0,
                "swing_direction": "right"  # alap érték, AI módosíthatja
            })

        # Ablak felismerés
        elif line.startswith("W"):
            initial_structure["windows"].append({
                "x": None,
                "y": None,
                "width": None,
                "angle": 0
            })

        # Méret felismerés (pl. 3.5m)
        elif "m" in line:
            try:
                size = float(line.replace("m", "").strip())
                # Ha van legalább 1 szoba, ideiglenesen hozzáadhatjuk
                if initial_structure["rooms"]:
                    initial_structure["rooms"][-1]["size"] = size
            except ValueError:
                continue

    # --- AI feldolgozás: pontos koordináták és méretek generálása ---
    if not initial_structure["rooms"]:
        initial_structure["rooms"].append({"name": "Sketch Room", "points": []})
    prompt = "Generate exact coordinates and dimensions for this building sketch based on OCR detection."
    final_structure = generate_or_modify_structure(prompt, initial_structure)

    return final_structure
