import ezdxf
from typing import Dict, Any
import os
import math

# --- Abszolút útvonal létrehozása az output mappához ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # backend/app
OUTPUT_DIR = os.path.join(BASE_DIR, "..", "..", "output")  # architect_ai/output
os.makedirs(OUTPUT_DIR, exist_ok=True)


def generate_dxf_from_structure(structure: Dict[str, Any], filename: str = "output.dxf") -> str:
    """
    Generál egy DXF fájlt a JSON struktúra alapján.

    structure: {
        "rooms": [{"name": "R1", "points": [[x1,y1], [x2,y2], ...]}],
        "doors": [{"x": , "y": , "width": , "angle": , "swing_direction": "left/right"}],
        "windows": [{"x": , "y": , "width": , "angle": 0}],
        "metadata": {"area": , "units": "m"}
    }
    """

    doc = ezdxf.new(dxfversion="R2010")
    msp = doc.modelspace()

    # --- Szobák rajzolása ---
    for room in structure.get("rooms", []):
        points = room.get("points", [])
        if len(points) < 3:
            continue  # polygonhoz legalább 3 pont kell

        # Polygon bezárása
        polygon_points = points + [points[0]]

        # LWPolyline létrehozása
        msp.add_lwpolyline(polygon_points, close=True)

        # Szoba név középre (átlag koordináták)
        x_avg = sum(p[0] for p in points) / len(points)
        y_avg = sum(p[1] for p in points) / len(points)
        msp.add_text(room["name"], dxfattribs={"height": 0.5}).set_pos((x_avg, y_avg))

    # --- Ajtók rajzolása ---
    for door in structure.get("doors", []):
        x, y = door["x"], door["y"]
        width = door["width"]
        angle = math.radians(door.get("angle", 0))
        swing = door.get("swing_direction", "right").lower()

        # Ajtó vonal
        x2 = x + width * math.cos(angle)
        y2 = y + width * math.sin(angle)
        msp.add_line((x, y), (x2, y2))

        # Swing ív (félkör)
        start_angle = math.degrees(angle)
        if swing == "left":
            end_angle = start_angle + 90
        else:
            end_angle = start_angle - 90
        msp.add_arc(center=(x, y), radius=width, start_angle=start_angle, end_angle=end_angle)

    # --- Ablakok rajzolása ---
    for window in structure.get("windows", []):
        x, y = window["x"], window["y"]
        width = window["width"]
        angle = math.radians(window.get("angle", 0))
        x2 = x + width * math.cos(angle)
        y2 = y + width * math.sin(angle)
        msp.add_line((x, y), (x2, y2))

    # --- Fájl mentése ---
    output_path = os.path.join(OUTPUT_DIR, filename)
    doc.saveas(output_path)

    return output_path
