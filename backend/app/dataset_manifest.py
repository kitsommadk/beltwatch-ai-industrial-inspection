"""Sanitized dataset-manifest contracts for BeltWatch model evaluation.

This module stores metadata contracts only. Proprietary image bytes, customer names,
work orders, plant identifiers, and other sensitive production data must not be
committed to the public repository.
"""

from dataclasses import dataclass, field
from enum import Enum


class DatasetSplit(str, Enum):
    TRAIN = "train"
    VALIDATION = "validation"
    TEST = "test"
    HOLDOUT = "holdout"


class SurfaceLabel(str, Enum):
    NORMAL = "normal"
    DEFECT = "defect"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class DatasetRecord:
    record_id: str
    asset_ref: str
    physical_run_id: str
    split: DatasetSplit
    surface_label: SurfaceLabel
    camera_id: str
    calibration_version: int
    lighting_profile: str
    material_profile: str
    speed_profile: str
    defect_labels: tuple[str, ...] = field(default_factory=tuple)
    notes: str = ""

    def __post_init__(self) -> None:
        for name, value in (
            ("record_id", self.record_id),
            ("asset_ref", self.asset_ref),
            ("physical_run_id", self.physical_run_id),
            ("camera_id", self.camera_id),
        ):
            if not value.strip():
                raise ValueError(f"{name} must not be empty")
        if self.calibration_version <= 0:
            raise ValueError("calibration_version must be greater than zero")
        if self.surface_label == SurfaceLabel.NORMAL and self.defect_labels:
            raise ValueError("normal records must not contain defect labels")


def validate_split_isolation(records: list[DatasetRecord]) -> None:
    """Prevent one physical belt/run from leaking across dataset splits.

    Adjacent frames from one physical run are highly correlated. Allowing the same
    run in training and test data can produce misleadingly strong benchmark scores.
    """
    splits_by_run: dict[str, set[DatasetSplit]] = {}
    for record in records:
        splits_by_run.setdefault(record.physical_run_id, set()).add(record.split)

    leaking = {
        run_id: splits
        for run_id, splits in splits_by_run.items()
        if len(splits) > 1
    }
    if leaking:
        details = "; ".join(
            f"{run_id}: {', '.join(sorted(split.value for split in splits))}"
            for run_id, splits in sorted(leaking.items())
        )
        raise ValueError(f"physical run appears in multiple dataset splits: {details}")
