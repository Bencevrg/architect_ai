from __future__ import annotations
from pydantic import BaseModel, Field
from typing import List, Literal


class Point(BaseModel):
    x: float
    y: float


class Room(BaseModel):
    name: str
    points: List[List[float]] = Field(..., description="[[x1,y1],[x2,y2],...]")


class Door(BaseModel):
    x: float
    y: float
    width: float
    angle: float = 0.0
    swing_direction: Literal["left","right"] = "right"


class Window(BaseModel):
    x: float
    y: float
    width: float
    angle: float = 0.0


class Metadata(BaseModel):
    area: float | None = None
    units: Literal["m"] = "m"


class Plan(BaseModel):
    rooms: List[Room]
    doors: List[Door] = []
    windows: List[Window] = []
    metadata: Metadata = Metadata()


class GenerateRequest(BaseModel):
    prompt: str
    existing_plan: Plan | None = None


class GenerateResponse(BaseModel):
    plan: Plan
    dxf_path: str