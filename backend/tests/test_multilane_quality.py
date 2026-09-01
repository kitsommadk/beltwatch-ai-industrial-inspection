import pytest

from app.multilane_span import _sample_rows, estimate_two_dark_belts


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
    assert a.span.left_edge_spread_px == 0
    assert b.span.right_edge_spread_px == 0


def test_lane_edge_wander_is_measured_independently():
    image = _image()
    rows = _sample_rows(len(image), 0.5, 5)
    for index, y in enumerate(rows):
        a_left = 8 + index
        b_left = 74 + index
        _paint(image[y], a_left, 45)
        _paint(image[y], b_left, 115)

    result = estimate_two_dark_belts(image, sample_count=5)
    a, b = result.lanes
    assert a.span.left_x == 10
    assert b.span.left_x == 76
    assert a.span.left_edge_spread_px == 4
    assert b.span.left_edge_spread_px == 4
    assert a.span.right_edge_spread_px == 0
    assert b.span.right_edge_spread_px == 0
    assert a.span.span_spread_px == 4
    assert b.span.span_spread_px == 4


def test_weakest_sampled_row_controls_edge_contrast():
    image = _image()
    rows = _sample_rows(len(image), 0.5, 5)
    for y in rows:
        _paint(image[y], 10, 45, 20)
        _paint(image[y], 75, 115, 20)
    weak_row = rows[0]
    _paint(image[weak_row], 10, 45, 80)

    result = estimate_two_dark_belts(image, sample_count=5)
    a, b = result.lanes
    assert a.span.min_edge_contrast == pytest.approx(150.0)
    assert b.span.min_edge_contrast == pytest.approx(210.0)
    assert a.span.min_edge_contrast < b.span.min_edge_contrast


def test_missing_second_belt_on_one_sampled_row_fails_closed():
    image = _image()
    for row in image:
        _paint(row, 10, 45)
        _paint(row, 75, 115)
    center = _sample_rows(len(image), 0.5, 5)[2]
    for x in range(75, 115):
        image[center][x] = 230

    with pytest.raises(ValueError, match=f"expected exactly two belt-like spans at row {center}, found 1"):
        estimate_two_dark_belts(image, sample_count=5)


def test_ambiguous_third_dark_region_fails_closed():
    image = _image()
    for row in image:
        _paint(row, 10, 45)
        _paint(row, 75, 115)
    center = _sample_rows(len(image), 0.5, 5)[2]
    _paint(image[center], 120, 140)

    with pytest.raises(ValueError, match=f"expected exactly two belt-like spans at row {center}, found 3"):
        estimate_two_dark_belts(image, sample_count=5)


def test_touching_belts_are_not_silently_split_into_two_lanes():
    image = _image()
    for row in image:
        _paint(row, 10, 65)
        _paint(row, 65, 115)

    with pytest.raises(ValueError, match="found 1"):
        estimate_two_dark_belts(image, sample_count=5)
