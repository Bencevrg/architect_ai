"""Pydantic sémák a backend és a frontend közötti JSON struktúrához."""

from typing import List

from pydantic import BaseModel, Field, field_validator


class Room(BaseModel):
    """Egy szoba sokszög koordinátákkal megadott leírása."""

    name: str
    points: List[List[float]] = Field(
        description="Sorba rendezett (x, y) pontok, az első és utolsó pont érintkezik."
    )

    @field_validator("points")
    @classmethod
    def validate_points(cls, value: List[List[float]]):
        if len(value) < 3:
            raise ValueError("A szobához legalább három pont szükséges.")
        return value


class Door(BaseModel):
    """Ajtó pozíciója és a nyitás iránya."""

    x: float
    y: float
    width: float = Field(gt=0)
    angle: float = 0.0
    swing_direction: str = Field(default="right", pattern=r"^(left|right)$")


class Window(BaseModel):
    """Ablak pozíciója és szélessége."""

    x: float
    y: float
    width: float = Field(gt=0)
    angle: float = 0.0


class Metadata(BaseModel):
    """Metainformációk a tervrajzról."""

    area: float | None = Field(default=None, ge=0)
    units: str = "m"


class BuildingStructure(BaseModel):
    """Teljes épület leírása szobákkal, ajtókkal, ablakokkal."""

    rooms: List[Room]
    doors: List[Door]
    windows: List[Window]
    metadata: Metadata
