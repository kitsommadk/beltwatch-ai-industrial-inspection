from typing import Literal

from pydantic import BaseModel, Field


SessionStatus = Literal["ready", "inspecting", "paused", "complete"]
ReviewStatus = Literal["open", "acknowledged", "false_positive"]


class SessionInput(BaseModel):
    roll_number: str = Field(min_length=1, max_length=80)
    work_order: str = Field(min_length=1, max_length=80)
    operator: str = Field(min_length=1, max_length=80)
    target_width_in: float = Field(gt=0, le=120)
    tolerance_in: float = Field(gt=0, le=2)
    target_length_ft: float = Field(gt=0, le=100_000)


class ProgressInput(BaseModel):
    delta_ft: float = Field(default=12, gt=0, le=500)


class EventReview(BaseModel):
    status: Literal["acknowledged", "false_positive"]
    note: str = Field(default="", max_length=500)


class DetectionRequest(BaseModel):
    kind: Literal["edge", "width", "surface"] = "edge"
    camera: Literal["Top", "Bottom"] | None = None


class EvidenceCaptureRequest(BaseModel):
    """Development capture input until a vision adapter supplies detected belt edges."""

    camera: Literal["top", "bottom"]
    measured_span_px: float = Field(gt=0, le=20_000)
