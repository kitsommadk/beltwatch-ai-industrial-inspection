import pytest

from app.edge_span import BeltSpan
from app.multilane_span import LaneSpan, MultiLaneSpan
from app.slit_diagnostics import derive_slit_pair_diagnostics


def _span(left, right):
    return BeltSpan(left, right, right-left, 10, 100.0)


def test_pair_diagnostics_preserve_gap_centers_and_total_span():
    result = MultiLaneSpan((
        LaneSpan("belt-a", _span(10, 45)),
        LaneSpan("belt-b", _span(70, 110)),
    ))
    diagnostics = derive_slit_pair_diagnostics(result)
    assert diagnostics.gap_px == 25
    assert diagnostics.belt_a_center_x_px == 27.5
    assert diagnostics.belt_b_center_x_px == 90.0
    assert diagnostics.center_distance_px == 62.5
    assert diagnostics.total_occupied_span_px == 100


def test_touching_lanes_have_zero_gap_without_being_called_overlap():
    result = MultiLaneSpan((
        LaneSpan("belt-a", _span(10, 45)),
        LaneSpan("belt-b", _span(45, 80)),
    ))
    assert derive_slit_pair_diagnostics(result).gap_px == 0


def test_pair_diagnostics_require_exact_lane_identity():
    result = MultiLaneSpan((
        LaneSpan("belt", _span(10, 45)),
        LaneSpan("belt-b", _span(70, 110)),
    ))
    with pytest.raises(ValueError, match="exactly belt-a and belt-b"):
        derive_slit_pair_diagnostics(result)
