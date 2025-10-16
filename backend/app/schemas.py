from pydantic import BaseModel
from typing import List

class Room(BaseModel):
    name: str
    x: float
    y: float
    w: float
    h: float

class Door(BaseModel):
    x: float
    y: float
    width: float
    angle: float

class Window(BaseModel):
    x: float
    y: float
    width: float

class BuildingStructure(BaseModel):
    rooms: List[Room]
    doors: List[Door]
    windows: List[Window]
    metadata: dict
