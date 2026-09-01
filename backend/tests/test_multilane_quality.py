import pytest

from app.multilane_span import estimate_two_dark_belts


def _image(width=140, height=25, value=230):
    return [[value for _ in range(width)] for _ in range(height)]


def _paint(row, left, right, value=20):
    for x in range(left, right):
        row[x] = value


def test_straight_two_lane_geometry_is_stable_across_rows():
    image = _image()
    for row in image:
        _paint(row, 10, 45)
        _paint(row, 75, 115)

    result = estimate_two_dark_belts(image, sample_count=5)
    a, b = result.lanes
    assert a.lane_id == "belt-a"
    assert b.lane_id == "belt-b"
    assert (a.span.left_x, a.span.right_x_exclusive, a.span.span_px) == (10, 45, 35)
    assert (b.span.left_x, b.span.right_x_exclusive, b.span.span_px) == (75, 115, 40)
    assert a.span.sampled_rows == 5
    assert b.span.sampled_rows == 5
    assert a.span.left_position_spread_px == 0
    assert b.span.right_position_spread_px == 0


def test_lane_edge_wander_is_measured_independently():
    image = _image()
    # The estimator samples rows 7, 9, 12, 15, 17 for a 25px image.
    sampled = {7: (8, 45, 74, 115), 9: (9, 45, 75, 115), 12: (10, 45, 76, 115), 15: (11, 45, 77, 115), 17: (12, 45, 78, 115)}
    for y, (a_left, a_right, b_left, b_right) in sampled.items():
        _paint(image[y], a_left, a_right)
        _paint(image[y], b_left, b_right)

    result = estimate_two_dark_belts(image, sample_count=5)
    a, b = result.lanes
    assert a.span.left_x == 10
    assert b.span.left_x == 76
    assert a.span.left_position_spread_px == 4
    assert b.span.left_position_spread_px == 4
    assert a.span.right_position_spread_px == 0
    assert b.span.right_position_spread_px == 0


def test_missing_second_belt_on_one_sampled_row_fails_closed():
    image = _image()
    for row in image:
        _paint(row, 10, 45)
        _paint(row, 75, 115)
    # Remove Belt B from the representative sampled row.
    for x in range(75, 115):
        image[12][x] = 230

    with pytest.raises(ValueError, match="expected exactly two belt-like spans at row 12, found 1"):
        estimate_two_dark_belts(image, sample_count=5)


def test_ambiguous_third_dark_region_fails_closed():
    image = _image()
    for row in image:
        _paint(row, 10, 45)
        _paint(row, 75, 115)
    _paint(image[12], 120, 140)

    with pytest.raises(ValueError, match="expected exactly two belt-like spans at row 12, found 3"):
        estimate_two_dark_belts(image, sample_count=5)


def test_touching_belts_are_not_silently_split_into_two_lanes():
    image = _image()
    for row in image:
        _paint(row, 10, 65)
        _paint(row, 65, 115)

    with pytest.raises(ValueError, match="found 1"):
        estimate_two_dark_belts(image, sample_count=5)
