"""Pairwise diagnostics derived from the same slit two-lane frame.

These values are deterministic observations, not root-cause classifications.
They are intended to help operators distinguish lane-specific width behavior from
shared movement without claiming why that behavior occurred.
"""

from dataclasses import dataclass

from .multilane_span import MultiLaneSpan


@dataclass(frozen=True)
class SlitPairDiagnostics:
    gap_px: int
    belt_a_center_x_px: float
    belt_b_center_x_px: float
    center_distance_px: float
    total_occupied_span_px: int


def derive_slit_pair_diagnostics(result: MultiLaneSpan) -> SlitPairDiagnostics:
    lanes = {lane.lane_id: lane.span for lane in result.lanes}
    if set(lanes) != {"belt-a", "belt-b"}:
        raise ValueError("slit pair diagnostics require exactly belt-a and belt-b")
    a = lanes["belt-a"]
    b = lanes["belt-b"]
    if a.left_x >= b.left_x:
        raise ValueError("belt-a must be left of belt-b in image coordinates")
    gap = b.left_x - a.right_x_exclusive
    if gap < 0:
        raise ValueError("slit lane spans must not overlap")
    a_center = (a.left_x + a.right_x_exclusive) / 2.0
    b_center = (b.left_x + b.right_x_exclusive) / 2.0
    return SlitPairDiagnostics(
        gap_px=gap,
        belt_a_center_x_px=a_center,
        belt_b_center_x_px=b_center,
        center_distance_px=b_center - a_center,
        total_occupied_span_px=b.right_x_exclusive - a.left_x,
    )
