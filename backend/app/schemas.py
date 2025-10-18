from typing import List, Optional

from pydantic import BaseModel, Field, validator


class Room(BaseModel):
    name: str
    points: List[List[float]] = Field(..., min_length=3)


class Door(BaseModel):
    x: float
    y: float
    width: float
    angle: float = 0.0
    swing_direction: str = "right"

    @validator("swing_direction")
    def validate_swing_direction(cls, value: str) -> str:
        if value.lower() not in {"left", "right"}:
            raise ValueError("swing_direction must be 'left' or 'right'")
        return value.lower()


class Window(BaseModel):
    x: float
    y: float
    width: float
    angle: float = 0.0


class Metadata(BaseModel):
    area: Optional[float]
    units: str = "m"


class BuildingStructure(BaseModel):
    rooms: List[Room]
    doors: List[Door]
    windows: List[Window]
    metadata: Metadata
