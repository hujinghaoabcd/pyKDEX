"""Tests for deterministic built-in datasets and generators."""

from __future__ import annotations

import numpy as np
import pytest

from pykdex import (
    load_bimodal_points,
    make_bimodal_events,
    make_moving_hotspot_events,
)


def test_bimodal_generator_is_deterministic():
    first = make_bimodal_events(25, random_state=7)
    second = make_bimodal_events(25, random_state=7)
    third = make_bimodal_events(25, random_state=8)
    np.testing.assert_array_equal(first.coordinates, second.coordinates)
    assert first.fingerprint == second.fingerprint
    assert first.fingerprint != third.fingerprint


def test_bimodal_dataset_is_complete_and_valid():
    dataset = load_bimodal_points(n_events=40, resolution=0.25, random_state=9)
    assert dataset.events.n_events == 40
    assert dataset.support is not None
    assert dataset.boundary is not None
    assert dataset.validate().valid
    assert dataset.support.n_points == 480


def test_bimodal_generator_validates_event_count():
    with pytest.raises(TypeError, match="integer"):
        make_bimodal_events(True)
    with pytest.raises(ValueError, match="at least two"):
        make_bimodal_events(1)


def test_moving_hotspot_is_deterministic_and_moves_forward() -> None:
    first = make_moving_hotspot_events(
        100,
        velocity=(2.0, 0.0),
        spatial_noise=0.0,
        random_state=7,
    )
    second = make_moving_hotspot_events(
        100,
        velocity=(2.0, 0.0),
        spatial_noise=0.0,
        random_state=7,
    )
    np.testing.assert_array_equal(first.spatial_coordinates, second.spatial_coordinates)
    correlation = np.corrcoef(first.times, first.spatial_coordinates[:, 0])[0, 1]
    assert correlation == pytest.approx(1.0)
    assert first.temporal.temporal_unit == "unit"
