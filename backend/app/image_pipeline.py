"""Kép feldolgozó modul az Architect AI backendhez."""

from __future__ import annotations

import io
from typing import Any, Dict, List

from PIL import Image

try:
    import pytesseract
    from pytesseract import TesseractNotFoundError
except Exception:  # pragma: no cover - opcionális függőség
    pytesseract = None
    TesseractNotFoundError = RuntimeError  # type: ignore

from app.llm_client import generate_or_modify_structure


def _extract_tokens_from_text(ocr_text: str) -> Dict[str, List[str]]:
    """Egyszerű tokenizáló az OCR szöveghez."""

    rooms: List[str] = []
    doors: List[str] = []
    windows: List[str] = []
    sizes: List[str] = []

    for raw_line in ocr_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        upper_line = line.upper()
        if upper_line.startswith("R"):
            rooms.append(line)
        elif upper_line.startswith("D"):
            doors.append(line)
        elif upper_line.startswith("W"):
            windows.append(line)
        elif "M" in upper_line:
            sizes.append(line)

    return {"rooms": rooms, "doors": doors, "windows": windows, "sizes": sizes}


async def process_image_to_structure(file) -> Dict[str, Any]:
    """PNG képet dolgoz fel, és alap JSON struktúrát ad vissza."""

    image_bytes = await file.read()
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

    ocr_text = ""
    if pytesseract is not None:
        try:
            ocr_text = pytesseract.image_to_string(image)
        except TesseractNotFoundError:
            ocr_text = ""

    tokens = _extract_tokens_from_text(ocr_text)

    initial_structure: Dict[str, Any] = {
        "rooms": [],
        "doors": [],
        "windows": [],
        "metadata": {"area": None, "units": "m"},
    }

    for name in tokens["rooms"]:
        label = name.split()[0]
        initial_structure["rooms"].append({"name": label, "points": []})

    for _ in tokens["doors"]:
        initial_structure["doors"].append(
            {
                "x": None,
                "y": None,
                "width": None,
                "angle": 0,
                "swing_direction": "right",
            }
        )

    for _ in tokens["windows"]:
        initial_structure["windows"].append(
            {
                "x": None,
                "y": None,
                "width": None,
                "angle": 0,
            }
        )

    for size in tokens["sizes"]:
        try:
            numeric = float(size.lower().replace("m", "").strip())
        except ValueError:
            continue
        if initial_structure["rooms"]:
            initial_structure["rooms"][-1]["approx_size"] = numeric

    prompt = "Generate exact coordinates and dimensions for this building sketch based on OCR detection."
    final_structure = generate_or_modify_structure(prompt, initial_structure)
    return final_structure
