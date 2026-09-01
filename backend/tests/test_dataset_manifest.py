import pytest

from app.dataset_manifest import (
    DatasetRecord,
    DatasetSplit,
    SurfaceLabel,
    validate_split_isolation,
)


def record(record_id: str, run_id: str, split: DatasetSplit) -> DatasetRecord:
    return DatasetRecord(
        record_id=record_id,
        asset_ref=f"sanitized://{record_id}.png",
        physical_run_id=run_id,
        split=split,
        surface_label=SurfaceLabel.NORMAL,
        camera_id="top",
        calibration_version=1,
        lighting_profile="controlled-led-v1",
        material_profile="rubber-generic",
        speed_profile="unknown",
    )


def test_same_physical_run_may_repeat_inside_one_split():
    records = [
        record("r1-frame-001", "run-001", DatasetSplit.TRAIN),
        record("r1-frame-002", "run-001", DatasetSplit.TRAIN),
        record("r2-frame-001", "run-002", DatasetSplit.TEST),
    ]
    validate_split_isolation(records)


def test_physical_run_cannot_leak_between_train_and_test():
    records = [
        record("r1-frame-001", "run-001", DatasetSplit.TRAIN),
        record("r1-frame-900", "run-001", DatasetSplit.TEST),
    ]
    with pytest.raises(ValueError, match="multiple dataset splits"):
        validate_split_isolation(records)


def test_normal_record_rejects_defect_labels():
    with pytest.raises(ValueError, match="normal records"):
        DatasetRecord(
            record_id="bad-normal",
            asset_ref="sanitized://bad.png",
            physical_run_id="run-003",
            split=DatasetSplit.TRAIN,
            surface_label=SurfaceLabel.NORMAL,
            camera_id="top",
            calibration_version=1,
            lighting_profile="controlled-led-v1",
            material_profile="rubber-generic",
            speed_profile="unknown",
            defect_labels=("tear",),
        )
