from __future__ import annotations
import math
import re
from typing import Optional
from .schemas import Plan, Room, Door, Window, Metadata
AREA_REGEX = re.compile(r"(\d+[\.,]?\d*)\s*(?:m2|m²|nm|négyzetméter|nm2|m)\b", re.IGNORECASE)
ROOMS_REGEX = re.compile(r"(\d+)\s*(?:szoba|hálószoba|szobás)", re.IGNORECASE)

class DummyLLM:
    """Nagyon egyszerű logika: a promptból kinyer area-t és szobaszámot,
    és téglalapra parcellázva legenerál egy tervet.
    """
    def generate(self, prompt: str) -> Plan:
        area = self._parse_area(prompt) or 60.0
        n_rooms = self._parse_rooms(prompt) or 3
        # téglalap oldalai (arány 1:0.66)
        width = math.sqrt(area)
        height = area / width
        # kicsit kerekítünk
        width = round(width, 2)
        height = round(height, 2)
        
        rooms = []
        # egyszerű sávos felosztás n_rooms szerint, függőlegesen
        band_height = height / n_rooms
        y0 = 0.0
        for i in range(n_rooms):
            y1 = y0 + band_height
            rooms.append(Room(
                name=f"R{i+1}",
                points=[[0.0, y0], [width, y0], [width, y1], [0.0, y1]]
            ))
            y0 = y1
        # ajtó: R1 alsó fal közepén, jobbra nyíló
        doors = [Door(x=width/2.0, y=0.0, width=0.9, angle=0.0, swing_direction="right")]
        # 2 ablak a felső falon
        windows = [
            Window(x=width*0.33, y=height, width=1.2, angle=180.0),
            Window(x=width*0.66, y=height, width=1.2, angle=180.0)
        ]
        
        return Plan(
            rooms=rooms,
            doors=doors,
            windows=windows,
            metadata=Metadata(area=area, units="m")
        )
        
    def modify(self, plan: Plan, instruction: str) -> Plan:
        # primitív példák:
        # "R2 nagyobb 1 méterrel" → R2 sávját feljebb tolja
        # "ajtó jobbra 0.5 m" → ajtó x + 0.5
        m = re.search(r"R(\d+)\s*(?:nagyobb|nagyobbra)\s*(\d+[\.,]?\d*)\s*m", instruction, re.IGNORECASE)
        if m:
            idx = int(m.group(1)) - 1
            delta = float(m.group(2).replace(",", "."))
            if 0 <= idx < len(plan.rooms):
                # növeljük a kijelölt szoba magasságát delta-val, és utána toljuk a felette lévőket
                r = plan.rooms[idx]
                # feltételezzük: téglalap, points[0]=bal-alsó, [1]=jobb-alsó, [2]=jobb-felső, [3]=bal-felső
                h = r.points[2][1] - r.points[1][1]
                new_h = max(0.5, h + delta)
                dh = new_h - h
                r.points[2][1] += dh
                r.points[3][1] += dh
                # a felette lévő szobák Y koordinátáit is toljuk
                for j in range(idx+1, len(plan.rooms)):
                    for p in plan.rooms[j].points:
                        p[1] += dh
        m2 = re.search(r"ajtó\s*(?:jobbra|balra)\s*(\d+[\.,]?\d*)\s*m", instruction, re.IGNORECASE)
        if m2 and plan.doors:
            delta = float(m2.group(1).replace(",", "."))
            dir_right = "jobbra" in instruction.lower()
            plan.doors[0].x += delta if dir_right else -delta
        return plan
    
    def _parse_area(self, prompt: str) -> Optional[float]:
        m = AREA_REGEX.search(prompt)
        if not m:
            return None
        val = float(m.group(1).replace(",", "."))
        # ha a promptban csak egy szám + m van, feltételezzük, hogy m^2
        return val
    
    def _parse_rooms(self, prompt: str) -> Optional[int]:
        m = ROOMS_REGEX.search(prompt)
        return int(m.group(1)) if m else None
client = DummyLLM()