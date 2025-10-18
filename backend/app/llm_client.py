"""LLM kliens, amely OpenAI vagy dummy motorral is képes struktúrát generálni."""

from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

try:  # Az openai csomag opcionális, dummy módban nem szükséges.
    from openai import OpenAI  # type: ignore
except Exception:  # pragma: no cover - csak importhibákra
    OpenAI = None  # type: ignore


load_dotenv()


def _polygon_area(points: List[List[float]]) -> float:
    """Egyszerű sokszög-terület számítás a shoelace formulával."""

    if len(points) < 3:
        return 0.0

    area = 0.0
    for i, (x1, y1) in enumerate(points):
        x2, y2 = points[(i + 1) % len(points)]
        area += x1 * y2 - x2 * y1
    return abs(area) / 2.0


def _ensure_numeric(value: Optional[float], default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalise_structure(structure: Dict[str, Any]) -> Dict[str, Any]:
    """Kiegészíti a hiányzó mezőket, és biztosítja a konzisztens formátumot."""

    rooms: List[Dict[str, Any]] = []
    for idx, room in enumerate(structure.get("rooms", []), start=1):
        points = room.get("points") or []
        if len(points) < 3:
            # Ha hiányoznak a pontok, generálunk egy alap téglalapot.
            base_x = (idx - 1) * 4.0
            points = [
                [base_x, 0.0],
                [base_x + 3.0, 0.0],
                [base_x + 3.0, 3.0],
                [base_x, 3.0],
            ]
        rooms.append({
            "name": room.get("name") or f"Room {idx}",
            "points": [[float(x), float(y)] for x, y in points],
        })

    doors: List[Dict[str, Any]] = []
    for door in structure.get("doors", []):
        doors.append(
            {
                "x": _ensure_numeric(door.get("x"), 1.0),
                "y": _ensure_numeric(door.get("y"), 0.0),
                "width": max(_ensure_numeric(door.get("width"), 0.9), 0.1),
                "angle": _ensure_numeric(door.get("angle"), 0.0),
                "swing_direction": (door.get("swing_direction") or "right").lower(),
            }
        )

    windows: List[Dict[str, Any]] = []
    for window in structure.get("windows", []):
        windows.append(
            {
                "x": _ensure_numeric(window.get("x"), 1.0),
                "y": _ensure_numeric(window.get("y"), 1.0),
                "width": max(_ensure_numeric(window.get("width"), 1.2), 0.2),
                "angle": _ensure_numeric(window.get("angle"), 0.0),
            }
        )

    if not rooms:
        rooms = [
            {
                "name": "Living Room",
                "points": [[0.0, 0.0], [5.0, 0.0], [5.0, 4.0], [0.0, 4.0]],
            },
            {
                "name": "Bedroom",
                "points": [[5.0, 0.0], [9.0, 0.0], [9.0, 4.0], [5.0, 4.0]],
            },
            {
                "name": "Bathroom",
                "points": [[0.0, 4.0], [3.0, 4.0], [3.0, 6.0], [0.0, 6.0]],
            },
        ]

    total_area = sum(_polygon_area(room["points"]) for room in rooms)
    metadata = structure.get("metadata", {})
    metadata = {
        "area": _ensure_numeric(metadata.get("area"), round(total_area, 2)),
        "units": metadata.get("units") or "m",
    }

    return {
        "rooms": rooms,
        "doors": doors or [
            {"x": 2.5, "y": 0.0, "width": 0.9, "angle": 0.0, "swing_direction": "right"}
        ],
        "windows": windows or [
            {"x": 2.0, "y": 4.0, "width": 1.5, "angle": 180.0},
            {"x": 7.0, "y": 2.0, "width": 1.2, "angle": 90.0},
        ],
        "metadata": metadata,
    }


@dataclass
class _LLMBackend:
    """Közös interfész az LLM backendekhez."""

    def generate_or_modify_structure(self, prompt: str, current_structure: Optional[dict]) -> Dict[str, Any]:  # pragma: no cover - interface
        raise NotImplementedError


class _OpenAIBackend(_LLMBackend):
    def __init__(self, api_key: str) -> None:
        if OpenAI is None:  # pragma: no cover - csak akkor fut, ha a csomag hiányzik
            raise RuntimeError("Az openai csomag nem elérhető, dummy mód szükséges.")
        self._client = OpenAI(api_key=api_key)

    def generate_or_modify_structure(
        self, prompt: str, current_structure: Optional[dict]
    ) -> Dict[str, Any]:
        system_prompt = """
You are an AI architect.
You are given a house description or modification instruction.
Return ONLY valid JSON with the following structure:
- rooms: list of {"name": str, "points": [[x, y], ...]}
- doors: list of {"x": float, "y": float, "width": float, "angle": float, "swing_direction": str}
- windows: list of {"x": float, "y": float, "width": float, "angle": float}
- metadata: {"area": float, "units": "m"}
Rules:
1. If current design is provided, modify it according to the instruction.
2. If data is missing, generate plausible values logically.
3. Do not delete existing elements unless explicitly instructed.
4. Coordinates should be realistic and consistent.
5. Use meters for all units.
"""

        user_prompt = prompt
        if current_structure:
            user_prompt = (
                "Modify the existing building structure according to this instruction:\n"
                f"{prompt}\n\nExisting structure:\n{json.dumps(current_structure)}"
            )

        response = self._client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=2000,
        )

        content = response.choices[0].message.content.strip()
        data = json.loads(content)
        return _normalise_structure(data)


class _DummyBackend(_LLMBackend):
    """Egyszerű determinisztikus fallback, ha nincs OpenAI kulcs."""

    def generate_or_modify_structure(
        self, prompt: str, current_structure: Optional[dict]
    ) -> Dict[str, Any]:
        structure = current_structure or {}

        # Dummy logika: ha a promptban szerepel szám a négyzetméterre, beírjuk a metadata-ba.
        target_area = None
        for token in prompt.replace(",", " ").split():
            try:
                value = float(token)
            except ValueError:
                continue
            if value > 10:  # valószínűleg terület
                target_area = value
                break

        normalised = _normalise_structure(structure)

        if target_area is not None:
            normalised["metadata"]["area"] = round(float(target_area), 2)

        # Egyszerű ajtómozgatás: ha "jobbra" szerepel a promptban, toljuk el az első ajtót.
        if normalised["doors"] and "jobbra" in prompt.lower():
            normalised["doors"][0]["x"] += 0.5

        if normalised["doors"] and "balra" in prompt.lower():
            normalised["doors"][0]["x"] -= 0.5

        if normalised["rooms"] and "nagyobb" in prompt.lower():
            # Az első szoba szélességét növeljük egy méterrel.
            points = normalised["rooms"][0]["points"]
            if len(points) >= 4:
                # téglalap feltételezés - módosítjuk a jobb oldali pontokat
                max_x = max(p[0] for p in points)
                for point in points:
                    if math.isclose(point[0], max_x, abs_tol=1e-3):
                        point[0] += 1.0
                normalised["metadata"]["area"] = round(
                    sum(_polygon_area(room["points"]) for room in normalised["rooms"]), 2
                )

        return normalised


def _select_backend() -> _LLMBackend:
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        try:
            return _OpenAIBackend(api_key)
        except Exception:  # pragma: no cover - openai hibák esetén
            pass
    return _DummyBackend()


_BACKEND = _select_backend()


def generate_or_modify_structure(prompt: str, current_structure: Optional[dict] = None) -> Dict[str, Any]:
    """Publikus függvény a tervrajz generálásához / módosításához."""

    return _BACKEND.generate_or_modify_structure(prompt, current_structure)
