from typing import Literal

from pydantic import BaseModel, Field, model_validator


SessionStatus = Literal["ready", "inspecting", "paused", "complete"]
ReviewStatus = Literal["open", "acknowledged", "false_positive"]
RunLayoutInput = Literal["single", "slit-two-lane"]


class SessionInput(BaseModel):
    roll_number: str = Field(min_length=1, max_length=80)
    work_order: str = Field(min_length=1, max_length=80)
    operator: str = Field(min_length=1, max_length=80)
    target_width_in: float = Field(gt=0, le=120)
    tolerance_in: float = Field(gt=0, le=2)
    target_length_ft: float = Field(gt=0, le=100_000)
    run_layout: RunLayoutInput = "single"
    lane_targets: dict[Literal["belt-a", "belt-b"], float] | None = None

    @model_validator(mode="after")
    def validate_lane_targets(self):
        if self.run_layout == "single":
            if self.lane_targets is not None:
                raise ValueError("single-belt sessions must not provide slit lane targets")
            return self
        if self.lane_targets is None or set(self.lane_targets) != {"belt-a", "belt-b"}:
            raise ValueError("slit-two-lane sessions require exactly belt-a and belt-b target widths")
        if any(width <= 0 or width > 120 for width in self.lane_targets.values()):
            raise ValueError("lane target widths must be greater than 0 and at most 120 inches")
        return self


class ProgressInput(BaseModel):
    delta_ft: float = Field(default=12, gt=0, le=500)


class EventReview(BaseModel):
    status: Literal["acknowledged", "false_positive"]
    note: str = Field(default="", max_length=500)


class DetectionRequest(BaseModel):
    kind: Literal["edge", "width", "surface"] = "edge"
    camera: Literal["Top", "Bottom"] | None = None


class EvidenceCaptureRequest(BaseModel):
    """Development compatibility input where the caller supplies pixel span."""
    camera: Literal["top", "bottom"]
    measured_span_px: float = Field(gt=0, le=20_000)


class EvidenceAutoCaptureRequest(BaseModel):
    """Automatic image-driven capture request for replay/live-image providers."""
    camera: Literal["top", "bottom"]
