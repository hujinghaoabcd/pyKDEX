# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

from __future__ import annotations

from typing import Any

import numpy as np
import pytest

from pykdex import (
    GridSupport,
    NetworkTimeWorkspace,
    NetworkWorkspace,
    SpatialEvents,
    SpatiotemporalGridSupport,
    load_t_junction,
)
from pykdex.risk import ExposureField
from pykdex.risk.support import describe_measured_support
from pykdex.uncertainty import (
    BootstrapPlan,
    BootstrapResult,
    FieldEnsemble,
    bootstrap_event_rate,
    pointwise_percentile_interval,
)


def _support(kind: str) -> Any:
    grid = GridSupport.from_bounds(
        (0.0, 0.0, 1.0, 1.0),
        resolution=0.5,
        spatial_unit="km",
    )
    if kind == "spatial":
        return grid
    if kind == "spatiotemporal":
        return SpatiotemporalGridSupport.from_spatial_grid(
            grid,
            temporal_resolution=1.0,
            temporal_unit="hours",
            temporal_bounds=(0.0, 2.0),
            temporal_origin="study-hour-zero",
            timezone="UTC",
        )

    network = load_t_junction().network
    raw = SpatialEvents.from_array(
        [[-0.75, 0.0], [0.50, 0.0]],
        crs=network.crs,
        spatial_unit=network.spatial_unit,
    )
    if kind == "network":
        return NetworkWorkspace.prepare(
            network,
            raw,
            lixel_length=0.5,
            max_snap_distance=0.05,
        ).lixels
    if kind == "network_time":
        return NetworkTimeWorkspace.prepare(
            network,
            raw,
            [0.25, 1.25],
            temporal_unit="hours",
            lixel_length=0.5,
            temporal_resolution=1.0,
            temporal_bounds=(0.0, 2.0),
            temporal_origin="study-hour-zero",
            timezone="UTC",
            max_snap_distance=0.05,
        ).arixels
    raise AssertionError(f"unknown support kind: {kind}")


def _intensity_bootstrap(
    support: Any,
    *,
    field_family: str = "intensity",
    valid_mask: np.ndarray | None = None,
    operation: str = "bootstrap_kde",
    estimator_family: str = "synthetic",
) -> BootstrapResult:
    descriptor = describe_measured_support(support)
    n_elements = descriptor.n_elements
    observed = np.linspace(1.0, 2.0, n_elements)
    replicates = np.vstack((0.5 * observed, observed, 1.5 * observed))
    valid = (
        np.ones(n_elements, dtype=bool)
        if valid_mask is None
        else np.asarray(valid_mask, dtype=bool)
    )
    observed = observed.copy()
    replicates = replicates.copy()
    observed[~valid] = np.nan
    replicates[:, ~valid] = np.nan
    ensemble = FieldEnsemble(
        replicate_values=replicates,
        observed_values=observed,
        support=support,
        field_family=field_family,
        observed_field_fingerprint="observed-intensity",
        replicate_source_fingerprints=("replicate-0", "replicate-1", "replicate-2"),
        resampling_method="ordinary",
        seed_ledger_fingerprint="seed-ledger",
        execution_metadata={"parallel_axis": "none"},
        valid_mask=valid,
        metadata={"conditional_on_observed_event_count": True},
    )
    plan = BootstrapPlan(
        n_resamples=3,
        confidence_level=0.8,
        random_state=13,
    )
    interval = pointwise_percentile_interval(
        ensemble,
        confidence_level=plan.confidence_level,
    )
    return BootstrapResult(
        ensemble=ensemble,
        interval=interval,
        plan=plan,
        operation=operation,
        estimator_family=estimator_family,
        seed_metadata={
            "seed_ledger_fingerprint": "seed-ledger",
            "n_logical_tasks": 3,
        },
        metadata={"source": "synthetic-test"},
    )


@pytest.mark.parametrize(
    ("kind", "expected_descriptor_kind"),
    [
        ("spatial", "spatial_grid"),
        ("network", "network_lixel"),
        ("spatiotemporal", "spatiotemporal_grid"),
        ("network_time", "network_time_arixel"),
    ],
)
def test_fixed_exposure_event_rate_transforms_all_measured_intensity_families(
    kind: str,
    expected_descriptor_kind: str,
) -> None:
    support = _support(kind)
    source = _intensity_bootstrap(support, estimator_family=kind)
    exposure = ExposureField.from_density(
        np.full(source.ensemble.n_elements, 2.0),
        support,
        exposure_unit="person",
    )

    result = bootstrap_event_rate(
        source,
        exposure,
        event_unit="event",
    )

    assert result.operation == "bootstrap_event_rate"
    assert result.estimator_family == kind
    assert result.ensemble.field_family == "event_rate"
    assert result.ensemble.descriptor.kind == expected_descriptor_kind
    np.testing.assert_allclose(
        result.ensemble.replicate_values,
        source.ensemble.replicate_values / 2.0,
    )
    np.testing.assert_allclose(
        result.ensemble.observed_values,
        source.ensemble.observed_values / 2.0,
    )
    np.testing.assert_allclose(
        result.interval.estimate,
        source.ensemble.observed_values / 2.0,
    )
    np.testing.assert_allclose(
        result.interval.standard_error,
        source.interval.standard_error / 2.0,
    )
    assert result.plan is source.plan
    assert result.seed_metadata == source.seed_metadata
    assert result.metadata["fixed_exposure"] is True
    assert result.metadata["conditional_on_fixed_exposure"] is True
    assert result.metadata["event_uncertainty"] is True
    assert result.metadata["exposure_uncertainty"] is False
    assert result.metadata["rate_unit"] == "event/person"
    assert result.metadata["conditional_on_observed_event_count"] is True


def test_nan_policy_combines_source_and_exposure_invalid_masks() -> None:
    support = _support("spatial")
    n_elements = describe_measured_support(support).n_elements
    source_valid = np.ones(n_elements, dtype=bool)
    source_valid[1] = False
    source = _intensity_bootstrap(support, valid_mask=source_valid)
    exposure_values = np.ones(n_elements)
    exposure_values[2] = 0.0
    exposure = ExposureField.from_density(
        exposure_values,
        support,
        exposure_unit="person",
    )

    result = bootstrap_event_rate(
        source,
        exposure,
        event_unit="event",
        zero_policy="nan",
    )

    expected_valid = source_valid.copy()
    expected_valid[2] = False
    np.testing.assert_array_equal(result.ensemble.valid_mask, expected_valid)
    assert np.all(np.isnan(result.ensemble.replicate_values[:, ~expected_valid]))
    assert np.all(np.isnan(result.ensemble.observed_values[~expected_valid]))
    assert np.all(np.isnan(result.interval.lower[~expected_valid]))
    assert result.metadata["invalid_denominator_count"] == 1
    assert result.metadata["source_invalid_count"] == 1
    assert result.metadata["output_invalid_count"] == 2


def test_raise_policy_fails_before_output_for_zero_exposure() -> None:
    support = _support("spatial")
    source = _intensity_bootstrap(support)
    values = np.ones(source.ensemble.n_elements)
    values[0] = 0.0
    exposure = ExposureField.from_density(values, support, exposure_unit="person")

    with pytest.raises(ValueError, match="Denominator policy rejected 1 value"):
        bootstrap_event_rate(source, exposure, event_unit="event")


def test_minimum_policy_uses_only_the_explicit_floor() -> None:
    support = _support("spatial")
    source = _intensity_bootstrap(support)
    values = np.ones(source.ensemble.n_elements)
    values[0] = 0.0
    exposure = ExposureField.from_density(values, support, exposure_unit="person")

    result = bootstrap_event_rate(
        source,
        exposure,
        event_unit="event",
        zero_policy="minimum",
        minimum_denominator=0.25,
    )

    assert np.all(result.ensemble.valid_mask)
    np.testing.assert_allclose(
        result.ensemble.replicate_values[:, 0],
        source.ensemble.replicate_values[:, 0] / 0.25,
    )
    assert result.metadata["invalid_denominator_count"] == 1
    assert result.metadata["adjusted_denominator_count"] == 1
    assert result.metadata["minimum_denominator"] == pytest.approx(0.25)


def test_validity_threshold_is_explicit_for_nan_policy() -> None:
    support = _support("spatial")
    source = _intensity_bootstrap(support)
    values = np.ones(source.ensemble.n_elements)
    values[0] = 0.1
    exposure = ExposureField.from_density(values, support, exposure_unit="person")

    result = bootstrap_event_rate(
        source,
        exposure,
        event_unit="event",
        zero_policy="nan",
        validity_threshold=0.1,
    )

    assert not result.ensemble.valid_mask[0]
    assert np.all(np.isnan(result.ensemble.replicate_values[:, 0]))
    assert result.metadata["validity_threshold"] == pytest.approx(0.1)


def test_statistical_fingerprint_does_not_depend_on_memory_budget() -> None:
    support = _support("spatial")
    source = _intensity_bootstrap(support)
    exposure = ExposureField.from_density(
        np.ones(source.ensemble.n_elements),
        support,
        exposure_unit="person",
    )

    unbounded = bootstrap_event_rate(source, exposure, event_unit="event")
    bounded = bootstrap_event_rate(
        source,
        exposure,
        event_unit="event",
        memory_budget_bytes=10_000_000,
    )

    assert (
        unbounded.ensemble.observed_field_fingerprint
        == bounded.ensemble.observed_field_fingerprint
    )
    assert (
        unbounded.ensemble.replicate_source_fingerprints
        == bounded.ensemble.replicate_source_fingerprints
    )
    np.testing.assert_array_equal(
        unbounded.ensemble.replicate_values,
        bounded.ensemble.replicate_values,
    )


def test_different_fixed_exposure_changes_derived_field_identity() -> None:
    support = _support("spatial")
    source = _intensity_bootstrap(support)
    first = ExposureField.from_density(
        np.ones(source.ensemble.n_elements),
        support,
        exposure_unit="person",
    )
    second = ExposureField.from_density(
        np.full(source.ensemble.n_elements, 2.0),
        support,
        exposure_unit="person",
    )

    first_result = bootstrap_event_rate(source, first, event_unit="event")
    second_result = bootstrap_event_rate(source, second, event_unit="event")

    assert (
        first_result.ensemble.observed_field_fingerprint
        != second_result.ensemble.observed_field_fingerprint
    )


def test_source_bootstrap_and_exposure_remain_immutable() -> None:
    support = _support("spatial")
    source = _intensity_bootstrap(support)
    exposure = ExposureField.from_density(
        np.full(source.ensemble.n_elements, 2.0),
        support,
        exposure_unit="person",
    )
    source_fingerprint = source.fingerprint
    exposure_fingerprint = exposure.fingerprint
    source_values = source.ensemble.replicate_values.copy()

    bootstrap_event_rate(source, exposure, event_unit="event")

    assert source.fingerprint == source_fingerprint
    assert exposure.fingerprint == exposure_fingerprint
    np.testing.assert_array_equal(source.ensemble.replicate_values, source_values)


def test_memory_budget_fails_before_complete_output_allocation() -> None:
    support = _support("spatial")
    source = _intensity_bootstrap(support)
    exposure = ExposureField.from_density(
        np.ones(source.ensemble.n_elements),
        support,
        exposure_unit="person",
    )

    with pytest.raises(MemoryError, match="estimated peak"):
        bootstrap_event_rate(
            source,
            exposure,
            event_unit="event",
            memory_budget_bytes=1,
        )


@pytest.mark.parametrize("invalid_budget", [True, 0, -1, 1.5])
def test_memory_budget_contract_is_closed(invalid_budget: object) -> None:
    support = _support("spatial")
    source = _intensity_bootstrap(support)
    exposure = ExposureField.from_density(
        np.ones(source.ensemble.n_elements),
        support,
        exposure_unit="person",
    )
    error = TypeError if invalid_budget in {True, 1.5} else ValueError

    with pytest.raises(error):
        bootstrap_event_rate(
            source,
            exposure,
            event_unit="event",
            memory_budget_bytes=invalid_budget,  # type: ignore[arg-type]
        )


def test_source_density_and_derived_operation_are_rejected() -> None:
    support = _support("spatial")
    exposure = ExposureField.from_density(
        np.ones(describe_measured_support(support).n_elements),
        support,
        exposure_unit="person",
    )

    with pytest.raises(ValueError, match="field_family='intensity'"):
        bootstrap_event_rate(
            _intensity_bootstrap(support, field_family="density"),
            exposure,
            event_unit="event",
        )
    with pytest.raises(ValueError, match="bootstrap_kde source"):
        bootstrap_event_rate(
            _intensity_bootstrap(support, operation="bootstrap_event_rate"),
            exposure,
            event_unit="event",
        )


def test_support_mismatch_and_invalid_public_inputs_are_rejected() -> None:
    support = _support("spatial")
    source = _intensity_bootstrap(support)
    other_support = GridSupport.from_bounds(
        (1.0, 1.0, 2.0, 2.0),
        resolution=0.5,
        spatial_unit="km",
    )
    other_exposure = ExposureField.from_density(
        np.ones(describe_measured_support(other_support).n_elements),
        other_support,
        exposure_unit="person",
    )
    exposure = ExposureField.from_density(
        np.ones(source.ensemble.n_elements),
        support,
        exposure_unit="person",
    )

    with pytest.raises(ValueError, match="same measured support fingerprint"):
        bootstrap_event_rate(source, other_exposure, event_unit="event")
    with pytest.raises(TypeError, match="intensity_bootstrap"):
        bootstrap_event_rate(object(), exposure, event_unit="event")  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="exposure"):
        bootstrap_event_rate(source, object(), event_unit="event")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="event_unit"):
        bootstrap_event_rate(source, exposure, event_unit="")
    with pytest.raises(TypeError, match="metadata"):
        bootstrap_event_rate(
            source,
            exposure,
            event_unit="event",
            metadata=[],  # type: ignore[arg-type]
        )
