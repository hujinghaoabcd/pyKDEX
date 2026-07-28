# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

from __future__ import annotations

import numpy as np
import pytest

from pykdex.core import (
    NetworkField,
    NetworkTimeField,
    SpatialKDEResult,
    SpatiotemporalKDEResult,
)
from pykdex.data import GridSupport, SpatiotemporalGridSupport
from pykdex.datasets import load_t_junction
from pykdex.network import LixelSupport
from pykdex.network_time import ArixelSupport
from pykdex.risk import (
    DenominatorPolicy,
    EventRateField,
    ExposureField,
    estimate_event_rate,
)
from pykdex.temporal import CyclicTimeDomain


def _grid() -> GridSupport:
    return GridSupport.from_bounds(
        (0.0, 0.0, 2.5, 1.0),
        resolution=1.0,
        crs="EPSG:3857",
        spatial_unit="m",
    )


def _spatial_result(
    support: GridSupport,
    values: np.ndarray | list[float],
    *,
    target: str = "intensity",
) -> SpatialKDEResult:
    return SpatialKDEResult(
        values=np.asarray(values, dtype=float),
        support=support.coordinates,
        bandwidth=1.0,
        target=target,
        kernel="gaussian",
        metric="euclidean",
        coordinate_names=support.coordinate_names,
        support_ids=support.ids,
        support_measure=support.measure,
        crs=support.crs,
        spatial_unit=support.spatial_unit,
        support_fingerprint=support.fingerprint,
        metadata={"support_shape": support.shape, "boundary_correction": "none"},
    )


def test_denominator_policy_validation_and_constructors() -> None:
    assert DenominatorPolicy.raise_invalid().mode == "raise"
    assert DenominatorPolicy.nan_invalid(validity_threshold=0.1).mode == "nan"
    assert DenominatorPolicy.minimum(0.25).minimum_denominator == pytest.approx(0.25)

    with pytest.raises(ValueError, match="mode"):
        DenominatorPolicy(mode="epsilon")
    with pytest.raises(ValueError, match="minimum_denominator"):
        DenominatorPolicy(mode="minimum")
    with pytest.raises(ValueError, match="positive"):
        DenominatorPolicy.minimum(0.0)
    with pytest.raises(ValueError, match="non-negative"):
        DenominatorPolicy(mode="raise", validity_threshold=-1.0)


def test_spatial_constant_rate_and_mass_identity() -> None:
    support = _grid()
    intensity = _spatial_result(support, np.full(support.n_points, 8.0))
    exposure = ExposureField.from_density(
        np.full(support.n_points, 2.0),
        support,
        exposure_unit="person_hours",
    )

    rate = estimate_event_rate(intensity, exposure, event_unit="events")

    assert isinstance(rate, EventRateField)
    assert np.allclose(rate.values, 4.0)
    assert rate.rate_unit == "events/person_hours"
    assert rate.event_mass == pytest.approx(20.0)
    assert rate.total_exposure == pytest.approx(5.0)
    assert rate.effective_exposure_total == pytest.approx(5.0)
    assert rate.exposure_weighted_mean_rate == pytest.approx(4.0)
    assert rate.effective_exposure_weighted_mean_rate == pytest.approx(4.0)
    assert rate.event_mass / rate.total_exposure == pytest.approx(4.0)
    assert rate.to_grid().shape == support.shape
    assert not rate.values.flags.writeable
    assert not rate.invalid_mask.flags.writeable
    assert (
        rate.fingerprint
        == estimate_event_rate(
            intensity,
            exposure,
            event_unit="events",
        ).fingerprint
    )


def test_event_and_exposure_scaling_laws() -> None:
    support = _grid()
    exposure = ExposureField.from_density(
        np.full(support.n_points, 4.0),
        support,
        exposure_unit="vehicles",
    )
    base = estimate_event_rate(
        _spatial_result(support, np.full(support.n_points, 6.0)),
        exposure,
        event_unit="crashes",
    )
    event_scaled = estimate_event_rate(
        _spatial_result(support, np.full(support.n_points, 18.0)),
        exposure,
        event_unit="crashes",
    )
    exposure_scaled = estimate_event_rate(
        _spatial_result(support, np.full(support.n_points, 6.0)),
        ExposureField.from_density(
            np.full(support.n_points, 8.0),
            support,
            exposure_unit="vehicles",
        ),
        event_unit="crashes",
    )

    assert np.allclose(event_scaled.values, 3.0 * base.values)
    assert np.allclose(exposure_scaled.values, 0.5 * base.values)


def test_zero_denominator_policies_are_explicit() -> None:
    support = _grid()
    intensity = _spatial_result(support, [2.0, 4.0, 6.0])
    exposure = ExposureField.from_density(
        [1.0, 0.0, 0.25],
        support,
        exposure_unit="person_hours",
    )

    with pytest.raises(ValueError, match="rejected 1 value"):
        estimate_event_rate(intensity, exposure, event_unit="events")

    nan_rate = estimate_event_rate(
        intensity,
        exposure,
        event_unit="events",
        zero_policy="nan",
    )
    assert np.allclose(nan_rate.values[[0, 2]], [2.0, 24.0])
    assert np.isnan(nan_rate.values[1])
    assert np.array_equal(nan_rate.invalid_mask, [False, True, False])
    assert not np.any(nan_rate.adjusted_mask)
    assert np.isnan(nan_rate.effective_exposure[1])
    assert nan_rate.to_frame()["invalid_denominator"].sum() == 1

    minimum_rate = estimate_event_rate(
        intensity,
        exposure,
        event_unit="events",
        zero_policy="minimum",
        minimum_denominator=0.5,
    )
    assert np.allclose(minimum_rate.effective_exposure, [1.0, 0.5, 0.5])
    assert np.allclose(minimum_rate.values, [2.0, 8.0, 12.0])
    assert np.array_equal(minimum_rate.invalid_mask, [False, True, False])
    assert np.array_equal(minimum_rate.adjusted_mask, [False, True, True])
    assert minimum_rate.metadata["adjusted_denominator_count"] == 2


def test_validity_threshold_and_policy_object_are_recorded() -> None:
    support = _grid()
    intensity = _spatial_result(support, [1.0, 1.0, 1.0])
    exposure = ExposureField.from_density(
        [1.0, 0.1, 0.5],
        support,
        exposure_unit="hours",
    )
    policy = DenominatorPolicy.nan_invalid(validity_threshold=0.2)
    rate = estimate_event_rate(
        intensity,
        exposure,
        event_unit="events",
        zero_policy=policy,
    )

    assert np.array_equal(rate.invalid_mask, [False, True, False])
    assert rate.metadata["validity_threshold"] == pytest.approx(0.2)
    with pytest.raises(ValueError, match="Do not combine"):
        estimate_event_rate(
            intensity,
            exposure,
            event_unit="events",
            zero_policy=policy,
            validity_threshold=0.2,
        )


def test_density_numerator_and_support_mismatch_are_rejected() -> None:
    support = _grid()
    exposure = ExposureField.from_density(
        [1.0, 1.0, 1.0],
        support,
        exposure_unit="persons",
    )
    with pytest.raises(ValueError, match="target='intensity'"):
        estimate_event_rate(
            _spatial_result(support, [1.0, 1.0, 1.0], target="density"),
            exposure,
            event_unit="events",
        )

    other = GridSupport.from_bounds(
        (1.0, 0.0, 3.5, 1.0),
        resolution=1.0,
        crs="EPSG:3857",
        spatial_unit="m",
    )
    with pytest.raises(ValueError, match="support fingerprints"):
        estimate_event_rate(
            _spatial_result(other, [1.0, 1.0, 1.0]),
            exposure,
            event_unit="events",
        )


def test_network_lixel_rate_uses_network_support() -> None:
    dataset = load_t_junction()
    lixels = LixelSupport.from_network(dataset.network, length=0.4)
    intensity = NetworkField(
        values=np.full(lixels.n_lixels, 6.0),
        support=lixels,
        bandwidth=0.8,
        target="intensity",
        kernel="gaussian",
        junction_policy="continuous",
        directed=False,
        network_fingerprint=dataset.network.fingerprint,
        event_fingerprint="network-events",
    )
    exposure = ExposureField.from_density(
        np.full(lixels.n_lixels, 3.0),
        lixels,
        exposure_unit="vehicle_hours",
    )

    rate = estimate_event_rate(intensity, exposure, event_unit="crashes")

    assert np.allclose(rate.values, 2.0)
    assert rate.descriptor.kind == "network_lixel"
    assert rate.metadata["source_metadata"]["junction_policy"] == "continuous"
    assert rate.event_mass == pytest.approx(6.0 * lixels.total_length)


def test_cyclic_spatiotemporal_grid_rate() -> None:
    spatial = GridSupport.from_bounds(
        (0.0, 0.0, 2.0, 1.0),
        resolution=1.0,
        spatial_unit="km",
    )
    support = SpatiotemporalGridSupport.from_spatial_grid(
        spatial,
        temporal_resolution=1.0,
        temporal_unit="hour",
        time_domain=CyclicTimeDomain(period=2.0),
    )
    intensity = SpatiotemporalKDEResult(
        values=np.full(support.n_points, 9.0),
        support=support,
        spatial_bandwidth=1.0,
        temporal_bandwidth=0.5,
        target="intensity",
        spatial_kernel="gaussian",
        temporal_kernel="gaussian",
        spatial_metric="euclidean",
    )
    exposure = ExposureField.from_density(
        np.full(support.n_points, 3.0),
        support,
        exposure_unit="person_hours",
    )

    rate = estimate_event_rate(intensity, exposure, event_unit="events")

    assert np.allclose(rate.values, 3.0)
    assert rate.descriptor.kind == "spatiotemporal_grid"
    assert rate.descriptor.time_domain_fingerprint == support.time_domain.fingerprint
    assert rate.to_grid().shape == support.shape


def test_cyclic_network_time_arixel_rate() -> None:
    dataset = load_t_junction()
    lixels = LixelSupport.from_network(dataset.network, length=0.5)
    support = ArixelSupport.from_lixels(
        lixels,
        temporal_resolution=1.0,
        temporal_unit="hour",
        time_domain=CyclicTimeDomain(period=2.0),
    )
    intensity = NetworkTimeField(
        values=np.full(support.n_arixels, 10.0),
        support=support,
        spatial_bandwidth=0.8,
        temporal_bandwidth=0.5,
        target="intensity",
        spatial_kernel="gaussian",
        temporal_kernel="gaussian",
        junction_policy="continuous",
        directed=False,
        network_fingerprint=dataset.network.fingerprint,
        event_fingerprint="network-time-events",
    )
    exposure = ExposureField.from_density(
        np.full(support.n_arixels, 2.0),
        support,
        exposure_unit="vehicle_hours",
    )

    rate = estimate_event_rate(intensity, exposure, event_unit="incidents")

    assert np.allclose(rate.values, 5.0)
    assert rate.descriptor.kind == "network_time_arixel"
    assert rate.descriptor.time_domain_fingerprint == support.time_domain.fingerprint
    assert rate.to_grid().shape == support.shape
