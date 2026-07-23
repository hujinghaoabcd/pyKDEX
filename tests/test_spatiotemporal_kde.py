# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

from math import pi

import numpy as np
import pytest

from pykdex import (
    CyclicTimeDomain,
    GridSupport,
    SpatiotemporalEvents,
    SpatiotemporalGridSupport,
    SpatiotemporalKDE,
    SpatiotemporalPointSupport,
    build_spatiotemporal_distance_asset,
)
from pykdex.core.exceptions import NotFittedError


def _events(*, weights: list[float] | None = None) -> SpatiotemporalEvents:
    return SpatiotemporalEvents.from_arrays(
        [[0.0], [1.0], [2.0]],
        [0.0, 1.0, 2.0],
        weights=weights,
        spatial_unit="km",
        temporal_unit="hours",
    )


def _support() -> SpatiotemporalPointSupport:
    return SpatiotemporalPointSupport.from_arrays(
        [[0.5], [1.5], [2.5]],
        [0.5, 1.5, 2.5],
        spatial_unit="km",
        temporal_unit="hours",
    )


def test_product_gaussian_matches_analytic_value() -> None:
    events = SpatiotemporalEvents.from_arrays(
        [[0.0]], [0.0], spatial_unit="km", temporal_unit="hours"
    )
    support = SpatiotemporalPointSupport.from_arrays(
        [[0.0]], [0.0], spatial_unit="km", temporal_unit="hours"
    )
    result = SpatiotemporalKDE(
        spatial_bandwidth=2.0,
        temporal_bandwidth=3.0,
    ).fit_predict(events, support)

    assert result.values[0] == pytest.approx(1.0 / (12.0 * pi))
    assert result.spatial_bandwidth == 2.0
    assert result.temporal_bandwidth == 3.0


def test_density_and_intensity_obey_weight_scaling() -> None:
    events = _events(weights=[1.0, 2.0, 3.0])
    support = _support()
    density = SpatiotemporalKDE(1.0, 1.0, target="density").fit_predict(events, support)
    intensity = SpatiotemporalKDE(1.0, 1.0, target="intensity").fit_predict(
        events, support
    )

    np.testing.assert_allclose(intensity.values, density.values * 6.0)


def test_chunking_and_distance_asset_reuse_are_invariant() -> None:
    events = _events()
    support = _support()
    asset = build_spatiotemporal_distance_asset(events, support)

    expected = (
        SpatiotemporalKDE(0.7, 0.9).fit(events).evaluate(support, distance_asset=asset)
    )
    actual = SpatiotemporalKDE(0.7, 0.9, chunk_size=1).fit(events).evaluate(support)
    np.testing.assert_allclose(actual, expected)


def test_distance_asset_fingerprint_mismatch_is_rejected() -> None:
    events = _events()
    support = _support()
    other = SpatiotemporalPointSupport.from_arrays(
        [[10.0]], [10.0], spatial_unit="km", temporal_unit="hours"
    )
    asset = build_spatiotemporal_distance_asset(events, support)

    with pytest.raises(ValueError, match="shape|fingerprint"):
        SpatiotemporalKDE(1.0, 1.0).fit(events).evaluate(other, distance_asset=asset)


def test_cyclic_gaussian_is_periodic_and_uses_image_sum() -> None:
    domain = CyclicTimeDomain(24.0)
    events = SpatiotemporalEvents.from_arrays(
        [[0.0]],
        [0.0],
        spatial_unit="km",
        temporal_unit="hours",
        time_domain=domain,
    )
    support = SpatiotemporalPointSupport.from_arrays(
        [[0.0], [0.0], [0.0]],
        [1.0, 23.0, 25.0],
        spatial_unit="km",
        temporal_unit="hours",
        time_domain=domain,
    )
    values = SpatiotemporalKDE(1.0, 10.0).fit(events).evaluate(support)

    assert values[0] == pytest.approx(values[1])
    assert values[0] == pytest.approx(values[2])
    minimum_distance_only = np.exp(-0.5 * (1.0 / 10.0) ** 2) / np.sqrt(2.0 * pi) / 10.0
    spatial_at_zero = 1.0 / np.sqrt(2.0 * pi)
    assert values[0] > spatial_at_zero * minimum_distance_only


def test_cyclic_density_conserves_mass_on_full_period_grid() -> None:
    domain = CyclicTimeDomain(24.0)
    events = SpatiotemporalEvents.from_arrays(
        [[0.0, 0.0]],
        [23.8],
        spatial_unit="km",
        temporal_unit="hours",
        time_domain=domain,
    )
    spatial = GridSupport.from_bounds(
        (-4.0, -4.0, 4.0, 4.0),
        resolution=0.2,
        spatial_unit="km",
    )
    support = SpatiotemporalGridSupport.from_spatial_grid(
        spatial,
        temporal_resolution=0.2,
        temporal_unit="hours",
        time_domain=domain,
    )
    result = SpatiotemporalKDE(0.5, 1.0, chunk_size=5_000).fit_predict(events, support)

    assert result.integral() == pytest.approx(1.0, abs=2e-4)
    assert result.to_grid().shape == support.shape
    assert len(result.to_frame()) == support.n_points


def test_unmeasured_result_refuses_integral_and_point_grid_conversion() -> None:
    result = SpatiotemporalKDE(1.0, 1.0).fit_predict(_events(), _support())
    with pytest.raises(ValueError, match="no support measure"):
        result.integral()
    with pytest.raises(ValueError, match="GridSupport"):
        result.to_grid()


def test_failed_refit_clears_previous_fitted_state() -> None:
    model = SpatiotemporalKDE(1.0, 1.0).fit(_events())
    with pytest.raises(TypeError, match="SpatiotemporalEvents"):
        model.fit(np.array([[0.0]]))  # type: ignore[arg-type]
    assert not model.is_fitted_
    with pytest.raises(NotFittedError):
        model.evaluate(_support())


def test_xarray_export_preserves_time_y_x_axes() -> None:
    xr = pytest.importorskip("xarray")
    del xr
    events = SpatiotemporalEvents.from_arrays(
        [[0.5, 0.5]], [0.5], temporal_unit="hours"
    )
    spatial = GridSupport.from_bounds((0, 0, 2, 2), resolution=1.0)
    support = SpatiotemporalGridSupport.from_spatial_grid(
        spatial,
        temporal_bounds=(0.0, 2.0),
        temporal_resolution=1.0,
        temporal_unit="hours",
    )
    exported = SpatiotemporalKDE(1.0, 1.0).fit_predict(events, support).to_xarray()

    assert exported.dims == ("time", "y", "x")
    assert exported.shape == (2, 2, 2)
