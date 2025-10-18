from __future__ import annotations
from math import cos, sin, radians
from pathlib import Path
import ezdxf
from .schemas import Plan, Room, Door, Window


ROOM_LAYER = "ROOMS"
DOOR_LAYER = "DOORS"
WINDOW_LAYER = "WINDOWS"
TEXT_LAYER = "TEXT"

def _centroid(points: list[list[float]]):
    x = sum(p[0] for p in points)/len(points)
    y = sum(p[1] for p in points)/len(points)
    return x, y




def add_room(msp, room: Room):
    msp.add_lwpolyline(room.points + [room.points[0]], dxfattribs={"layer": ROOM_LAYER, "closed": True})
    cx, cy = _centroid(room.points)
    msp.add_text(room.name, dxfattribs={"height": 0.3, "layer": TEXT_LAYER, "insert": (cx, cy)})





def add_door(msp, door: Door):
    # ajtó vonal + nyílás ív
    x, y = door.x, door.y
    w = door.width
    msp.add_line((x - w/2, y), (x + w/2, y), dxfattribs={"layer": DOOR_LAYER})
# ív a nyitásirány jelzésére: 90°-os ív
    radius = w
    start = 0 if door.swing_direction == "right" else 180
    end = 90 if door.swing_direction == "right" else 270
    msp.add_arc(center=(x, y), radius=radius, start_angle=start, end_angle=end, dxfattribs={"layer": DOOR_LAYER})




def add_window(msp, window: Window):
    # ablak mint rövid szakasz a falon, a szög figyelembevétele nélkül (MVP)
    x, y = window.x, window.y
    half = window.width/2
    msp.add_line((x - half, y), (x + half, y), dxfattribs={"layer": WINDOW_LAYER})




def plan_to_dxf(plan: Plan, out_path: str | Path) -> str:
    doc = ezdxf.new(setup=True)
    for layer in [ROOM_LAYER, DOOR_LAYER, WINDOW_LAYER, TEXT_LAYER]:
        if layer not in doc.layers:
            doc.layers.add(name=layer)
    msp = doc.modelspace()


    for r in plan.rooms:
        add_room(msp, r)
    for d in plan.doors:
        add_door(msp, d)
    for w in plan.windows:
        add_window(msp, w)


    out_path = str(out_path)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    doc.saveas(out_path)
    return out_path