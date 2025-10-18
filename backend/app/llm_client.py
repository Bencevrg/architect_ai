"""LLM integráció és dummy fallback a JSON alaprajz generálásához."""

from __future__ import annotations

import json
import math
import os
import re
import unicodedata
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

from app.schemas import BuildingStructure

try:  # pragma: no cover - opcionális OpenAI import
    from openai import OpenAI  # type: ignore
except Exception:  # pragma: no cover - tesztkörnyezetben nincs OpenAI csomag
    OpenAI = None  # type: ignore

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
USE_DUMMY = os.getenv("USE_DUMMY_LLM", "true").lower() in {"1", "true", "yes"}

if OPENAI_API_KEY and not USE_DUMMY and OpenAI is None:
    raise ImportError(
        "Az OpenAI csomag nincs telepítve, de OPENAI_API_KEY konfigurálva van. "
        "Telepítsd az openai csomagot vagy állítsd USE_DUMMY_LLM=true értékre."
    )

if OPENAI_API_KEY and not USE_DUMMY and OpenAI is not None:  # pragma: no cover
    _client: Optional[OpenAI] = OpenAI(api_key=OPENAI_API_KEY)  # type: ignore[call-arg]
else:
    _client = None


@dataclass
class DummyRoomSpec:
    label: str
    keyword: str


# --- Publikus API ---

def generate_or_modify_structure(
    prompt: str, current_structure: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Visszaad egy épületstruktúrát OpenAI-ból vagy a dummy generátorból."""

    if _client is not None:  # pragma: no cover - valós OpenAI hívás
        return _call_openai(prompt, current_structure)

    return _dummy_generate_or_modify(prompt, current_structure)


# --- OpenAI integráció ---

def _call_openai(prompt: str, current_structure: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    system_prompt = """
You are an AI architect.
You receive either a fresh house description or modification instructions.
Always respond with valid JSON containing:
- rooms: list of {name, points: [[x,y], ...]}
- doors: list of {x, y, width, angle, swing_direction}
- windows: list of {x, y, width, angle}
- metadata: {area, units}
Make realistic assumptions, keep geometry consistent, and preserve existing data unless instructed otherwise.
"""

    user_prompt = prompt
    if current_structure:
        user_prompt = (
            "Update the existing building structure according to the instruction below.\n"
            f"Instruction: {prompt}\n"
            f"Existing structure: {json.dumps(current_structure)}"
        )

    assert _client is not None  # mypy hint
    response = _client.chat.completions.create(  # type: ignore[union-attr]
        model=OPENAI_MODEL,
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        temperature=0.3,
        max_tokens=2000,
    )
    content = response.choices[0].message.content.strip()  # type: ignore[attr-defined]
    try:
        data = json.loads(content)
        BuildingStructure.model_validate(data)
        return data
    except (json.JSONDecodeError, ValueError) as exc:
        raise ValueError("Érvénytelen JSON választ adott az OpenAI modell.") from exc


# --- Dummy logika ---

_DUMMY_ROOMS: List[DummyRoomSpec] = [
    DummyRoomSpec(label="Living Room", keyword="nappali"),
    DummyRoomSpec(label="Kitchen", keyword="konyha"),
    DummyRoomSpec(label="Bathroom", keyword="fürd"),
    DummyRoomSpec(label="Dining", keyword="étkező"),
]


def _dummy_generate_or_modify(
    prompt: str, current_structure: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    if current_structure:
        structure = deepcopy(current_structure)
        _cleanup_room_metadata(structure)

        if _needs_regeneration(structure):
            structure = _dummy_generate_from_scratch(prompt)
            _apply_room_names_from_skeleton(structure, current_structure)
        else:
            structure = _apply_text_modifications(structure, prompt)
    else:
        structure = _dummy_generate_from_scratch(prompt)

    BuildingStructure.model_validate(structure)
    return structure


def _dummy_generate_from_scratch(prompt: str) -> Dict[str, Any]:
    prompt_lower = prompt.lower()
    area = _extract_number(prompt_lower, r"(\d+[\.,]?\d*)\s*(?:m2|négyzetméter|sqm|square meter)")
    if area is None:
        area = 68.0

    bedrooms = _extract_number(prompt_lower, r"(\d+)\s*(?:hálószoba|bedroom|szoba)")
    bedrooms = int(bedrooms) if bedrooms is not None else 2

    bathrooms = _extract_number(prompt_lower, r"(\d+)\s*(?:fürdő|bathroom)")
    bathrooms = int(bathrooms) if bathrooms is not None else 1

    has_kitchen = "konyha" in prompt_lower or "kitchen" in prompt_lower

    room_labels: List[str] = []
    for idx in range(1, bedrooms + 1):
        room_labels.append(f"Bedroom {idx}")
    for idx in range(1, bathrooms + 1):
        room_labels.append(f"Bathroom {idx}")

    if has_kitchen:
        room_labels.append("Kitchen")

    # Garantáljuk, hogy legalább egy nappali legyen
    room_labels.insert(0, "Living Room")

    total_rooms = len(room_labels)
    width = round(math.sqrt(area), 2)
    height = round(area / width, 2)
    segment_width = width / total_rooms

    rooms: List[Dict[str, Any]] = []
    windows: List[Dict[str, Any]] = []
    doors: List[Dict[str, Any]] = []

    current_x = 0.0
    for idx, label in enumerate(room_labels):
        next_x = width if idx == total_rooms - 1 else current_x + segment_width
        next_x = round(next_x, 2)
        room_points = [
            [round(current_x, 2), 0.0],
            [next_x, 0.0],
            [next_x, height],
            [round(current_x, 2), height],
        ]
        rooms.append({"name": label, "points": room_points})

        # Ablak a felső fal közepén
        window_x = round((current_x + next_x) / 2, 2)
        windows.append({"x": window_x, "y": height, "width": 1.2, "angle": 0.0})

        current_x = next_x

    # Főbejárat a nappali közepén
    living_room_width = rooms[0]["points"][1][0] - rooms[0]["points"][0][0]
    door_x = round(rooms[0]["points"][0][0] + living_room_width / 2, 2)
    doors.append({"x": door_x, "y": 0.0, "width": 0.9, "angle": 90.0, "swing_direction": "right"})

    metadata = {"area": round(width * height, 2), "units": "m"}

    structure = {"rooms": rooms, "doors": doors, "windows": windows, "metadata": metadata}
    return structure


def _apply_text_modifications(structure: Dict[str, Any], prompt: str) -> Dict[str, Any]:
    updated = deepcopy(structure)
    prompt_lower = prompt.lower()

    # Ajtó mozgatása
    door_shift = _extract_metric_delta(prompt_lower)
    if door_shift is not None and "ajt" in prompt_lower and updated.get("doors"):
        dx, dy = door_shift
        updated["doors"][0]["x"] = round(updated["doors"][0]["x"] + dx, 2)
        updated["doors"][0]["y"] = round(updated["doors"][0]["y"] + dy, 2)

    # Szoba méretének módosítása kulcsszavak alapján
    target_room_index = _match_room_index(updated["rooms"], prompt_lower)
    amount = _extract_number(prompt_lower, r"(\d+[\.,]?\d*)\s*m")
    if amount is None:
        amount = _extract_number_from_words(prompt_lower)
    if target_room_index is not None and amount is not None:
        delta = float(str(amount).replace(",", "."))
        if any(word in prompt_lower for word in ["csökk", "kisebb", "szűk"]):
            delta *= -1
        _resize_room(updated, target_room_index, delta)

    _recenter_windows(updated)
    _recalculate_metadata(updated)
    return updated


def _cleanup_room_metadata(structure: Dict[str, Any]) -> None:
    for room in structure.get("rooms", []):
        room.pop("size", None)


def _needs_regeneration(structure: Dict[str, Any]) -> bool:
    rooms = structure.get("rooms", [])
    if not rooms:
        return True
    for room in rooms:
        points = room.get("points") or []
        if len(points) < 3:
            return True
    return False


def _apply_room_names_from_skeleton(
    generated: Dict[str, Any], skeleton: Dict[str, Any]
) -> None:
    skeleton_names = [room.get("name") for room in skeleton.get("rooms", []) if room.get("name")]
    for room, name in zip(generated.get("rooms", []), skeleton_names):
        room["name"] = name


def _resize_room(structure: Dict[str, Any], index: int, delta: float) -> None:
    rooms = structure["rooms"]
    target = rooms[index]
    points = target["points"]
    left_x = points[0][0]
    right_x = points[1][0]
    new_right_x = round(right_x + delta, 2)
    if new_right_x <= left_x + 1e-3:
        return

    width_delta = new_right_x - right_x
    target["points"] = [
        [left_x, points[0][1]],
        [new_right_x, points[1][1]],
        [new_right_x, points[2][1]],
        [left_x, points[3][1]],
    ]

    # A szomszédos szobák eltolása, hogy ne legyenek átfedések
    for idx in range(index + 1, len(rooms)):
        rooms[idx]["points"] = [
            [round(p[0] + width_delta, 2), p[1]] for p in rooms[idx]["points"]
        ]

    # Ajtókat/ablakokat is toljuk, ha a határ túloldalán vannak
    for door in structure.get("doors", []):
        if door["x"] >= right_x:
            door["x"] = round(door["x"] + width_delta, 2)
    for window in structure.get("windows", []):
        if window["x"] >= right_x:
            window["x"] = round(window["x"] + width_delta, 2)


def _recenter_windows(structure: Dict[str, Any]) -> None:
    for room, window in zip(structure.get("rooms", []), structure.get("windows", [])):
        points = room["points"]
        center_x = round((points[0][0] + points[1][0]) / 2, 2)
        window["x"] = center_x
        window["y"] = points[2][1]


def _recalculate_metadata(structure: Dict[str, Any]) -> None:
    min_x = min(point[0] for room in structure["rooms"] for point in room["points"])
    max_x = max(point[0] for room in structure["rooms"] for point in room["points"])
    min_y = min(point[1] for room in structure["rooms"] for point in room["points"])
    max_y = max(point[1] for room in structure["rooms"] for point in room["points"])
    structure["metadata"] = {"area": round((max_x - min_x) * (max_y - min_y), 2), "units": "m"}


def _extract_number(text: str, pattern: str) -> Optional[float]:
    match = re.search(pattern, text)
    if not match:
        return None
    value = match.group(1).replace(",", ".")
    try:
        return float(value)
    except ValueError:
        return None


def _extract_metric_delta(text: str) -> Optional[tuple[float, float]]:
    amount = _extract_number(text, r"(\d+[\.,]?\d*)\s*m")
    if amount is None:
        amount = _extract_number_from_words(text)
    if amount is None:
        return None

    dx = dy = 0.0
    if "jobbra" in text or "right" in text:
        dx = amount
    if "balra" in text or "left" in text:
        dx = -amount
    if "fel" in text or "up" in text:
        dy = amount
    if "le" in text or "down" in text:
        dy = -amount
    if dx == 0 and dy == 0:
        dx = amount  # Alapértelmezett jobbra mozgatás
    return dx, dy


def _match_room_index(rooms: List[Dict[str, Any]], text: str) -> Optional[int]:
    for idx, room in enumerate(rooms):
        name = room["name"].lower()
        if any(keyword in text for keyword in [name, "room", "szoba", "bedroom"]):
            return idx
        for spec in _DUMMY_ROOMS:
            if spec.keyword in text and spec.label.lower() == name:
                return idx
    # Hálószoba keresése általános kulcsszó alapján
    if "hálószob" in text:
        for idx, room in enumerate(rooms):
            if "bedroom" in room["name"].lower():
                return idx
    return None


def _extract_number_from_words(text: str) -> Optional[float]:
    normalized = _strip_accents(text.lower())
    words = re.findall(r"[a-z]+", normalized)
    word_map = {
        "fel": 0.5,
        "masfel": 1.5,
        "egy": 1.0,
        "ket": 2.0,
        "ketto": 2.0,
        "harom": 3.0,
        "negy": 4.0,
        "ot": 5.0,
        "hat": 6.0,
        "het": 7.0,
        "nyolc": 8.0,
        "kilenc": 9.0,
        "tiz": 10.0,
    }
    for word in words:
        if word in word_map:
            return word_map[word]
    return None


def _strip_accents(text: str) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFD", text) if unicodedata.category(ch) != "Mn")
