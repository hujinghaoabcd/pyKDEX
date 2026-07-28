# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

from __future__ import annotations

import numpy as np
import pytest

from pykdex.data import (
    GridSupport,
    PointSupport,
    SpatiotemporalGridSupport,
    SpatiotemporalPointSupport,
)
from pykdex.datasets import load_t_junction
from pykdex.network import LixelSupport
from pykdex.network_time import ArixelSupport
from pykdex.risk import (
    ExposureField,
    describe_measured_support,
    require_same_measured_support,
)


def test_exposure_density_retains_measure_and_total() -> None:
    support = GridSupport.from_bounds((0.0, 0.0, 2.5, 1.0), resolution=1.0)
    field = ExposureField.from_density(
        [10.0, 20.0, 30.0],
        support,
        exposure_unit="persons",
    )

    assert field.representation == "density"
    assert field.descriptor.kind == "spatial_grid"
    assert np.allclose(field.descriptor.measure, [1.0, 1.0, 0.5])
    assert np.allclose(field.amounts, [10.0, 20.0, 15.0])
    assert field.total_exposure == pytest.approx(45.0)
    assert field.to_grid().shape == support.shape
    assert not field.values.flags.writeable
    assert not field.amounts.flags.writeable


def test_exposure_amount_constructor_recovers_density() -> None:
    support = GridSupport.from_bounds((0.0, 0.0, 2.5, 1.0), resolution=1.0)
    field = ExposureField.from_amounts(
        [10.0, 20.0, 15.0],
        support,
        exposure_unit="person_hours",
    )

    assert field.representation == "amount"
    assert np.allclose(field.density, [10.0, 20.0, 30.0])
    assert np.allclose(field.amounts, [10.0, 20.0, 15.0])
    assert field.total_exposure == pytest.approx(45.0)
    assert field.to_frame()["exposure_amount"].sum() == pytest.approx(45.0)


def test_exposure_field_fingerprint_is_content_stable() -> None:
    support = GridSupport.from_bounds((0.0, 0.0, 2.0, 1.0), resolution=1.0)
    first = ExposureField.from_density(
        [2.0, 3.0],
        support,
        exposure_unit="vehicles",
        metadata={"source": "fixture"},
    )
    second = ExposureField.from_density(
        np.array([2.0, 3.0]),
        support,
        exposure_unit="vehicles",
        metadata={"source": "fixture"},
    )
    changed = ExposureField.from_density(
        [2.0, 4.0],
        support,
        exposure_unit="vehicles",
        metadata={"source": "fixture"},
    )

    assert first.fingerprint == second.fingerprint
    assert first.fingerprint != changed.fingerprint


def test_zero_exposure_field_is_valid_for_inspection() -> None:
    support = GridSupport.from_bounds((0.0, 0.0, 2.0, 1.0), resolution=1.0)
    field = ExposureField.from_density(
        [0.0, 0.0],
        support,
        exposure_unit="persons",
    )

    assert field.is_zero
    assert field.total_exposure == 0.0


@pytest.mark.parametrize(
    "values, match",
    [
        ([1.0], "one exposure value"),
        ([1.0, -1.0], "non-negative"),
        ([1.0, np.inf], "finite"),
    ],
)
def test_exposure_field_rejects_invalid_density(
    values: list[float],
    match: str,
) -> None:
    support = GridSupport.from_bounds((0.0, 0.0, 2.0, 1.0), resolution=1.0)
    with pytest.raises(ValueError, match=match):
        ExposureField.from_density(values, support, exposure_unit="persons")


def test_exposure_field_requires_explicit_unit() -> None:
    support = GridSupport.from_bounds((0.0, 0.0, 1.0, 1.0), resolution=1.0)
    with pytest.raises(ValueError, match="exposure_unit"):
        ExposureField.from_density([1.0], support, exposure_unit="")


def test_unmeasured_point_support_is_rejected() -> None:
    support = PointSupport.from_array([[0.0, 0.0], [1.0, 0.0]])
    with pytest.raises(TypeError, match="support must be"):
        describe_measured_support(support)  # type: ignore[arg-type]


def test_unmeasured_spatiotemporal_points_are_rejected() -> None:
    support = SpatiotemporalPointSupport.from_arrays(
        [[0.0, 0.0], [1.0, 0.0]],
        [0.0, 1.0],
        temporal_unit="hour",
    )
    with pytest.raises(ValueError, match="support_measure"):
        ExposureField.from_density([1.0, 2.0], support, exposure_unit="persons")


def test_measured_spatiotemporal_points_are_supported() -> None:
    support = SpatiotemporalPointSupport.from_arrays(
        [[0.0, 0.0], [1.0, 0.0]],
        [0.0, 1.0],
        support_measure=[0.5, 2.0],
        temporal_unit="hour",
    )
    field = ExposureField.from_amounts(
        [5.0, 20.0],
        support,
        exposure_unit="person_hours",
    )

    assert field.descriptor.kind == "spatiotemporal_points"
    assert np.allclose(field.values, [10.0, 10.0])
    assert field.total_exposure == pytest.approx(25.0)


def test_network_lixel_exposure_uses_actual_lengths() -> None:
    dataset = load_t_junction()
    lixels = LixelSupport.from_network(dataset.network, length=0.4)
    amounts = np.arange(1, lixels.n_lixels + 1, dtype=float)
    field = ExposureField.from_amounts(
        amounts,
        lixels,
        exposure_unit="vehicle_hours",
    )

    assert field.descriptor.kind == "network_lixel"
    assert np.allclose(field.amounts, amounts)
    assert field.total_exposure == pytest.approx(float(np.sum(amounts)))
    assert np.allclose(field.values * lixels.lengths, amounts)


def test_space_time_grid_and_arixel_descriptors_preserve_domains() -> None:
    grid = GridSupport.from_bounds((0.0, 0.0, 2.0, 1.0), resolution=1.0)
    space_time = SpatiotemporalGridSupport.from_spatial_grid(
        grid,
        temporal_resolution=1.0,
        temporal_unit="hour",
        temporal_bounds=(0.0, 2.0),
    )
    dataset = load_t_junction()
    lixels = LixelSupport.from_network(dataset.network, length=0.5)
    arixels = ArixelSupport.from_lixels(
        lixels,
        temporal_resolution=1.0,
        temporal_unit="hour",
        temporal_bounds=(0.0, 2.0),
    )

    st_descriptor = describe_measured_support(space_time)
    nt_descriptor = describe_measured_support(arixels)

    assert st_descriptor.kind == "spatiotemporal_grid"
    assert nt_descriptor.kind == "network_time_arixel"
    assert st_descriptor.temporal_unit == "hour"
    assert nt_descriptor.temporal_unit == "hour"
    assert st_descriptor.time_domain_fingerprint is not None
    assert nt_descriptor.time_domain_fingerprint is not None
    assert st_descriptor.total_measure == pytest.approx(
        float(np.sum(space_time.measure))
    )
    assert nt_descriptor.total_measure == pytest.approx(float(np.sum(arixels.measure)))


def test_exact_support_identity_is_required() -> None:
    first = GridSupport.from_bounds((0.0, 0.0, 2.0, 1.0), resolution=1.0)
    equivalent = GridSupport.from_bounds((0.0, 0.0, 2.0, 1.0), resolution=1.0)
    different = GridSupport.from_bounds((0.0, 0.0, 3.0, 1.0), resolution=1.0)

    descriptor = require_same_measured_support(first, equivalent)
    assert descriptor.fingerprint == first.fingerprint
    with pytest.raises(ValueError, match="same measured support"):
        require_same_measured_support(first, different)
