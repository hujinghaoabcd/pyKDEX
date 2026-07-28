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
from pykdex.risk import RelativeRiskField, estimate_relative_risk
from pykdex.temporal import CyclicTimeDomain


def _grid() -> GridSupport:
    return GridSupport.from_bounds(
        (0.0, 0.0, 2.5, 1.0),
        resolution=1.0,
        crs="EPSG:3857",
        spatial_unit="m",
    )


def _spatial_density(
    support: GridSupport,
    values: np.ndarray | list[float],
    *,
    bandwidth: float | np.ndarray = 1.0,
    target: str = "density",
    kernel: str = "gaussian",
    metric: str = "euclidean",
    boundary_correction: str = "none",
) -> SpatialKDEResult:
    return SpatialKDEResult(
        values=np.asarray(values, dtype=float),
        support=support.coordinates,
        bandwidth=bandwidth,
        target=target,
        kernel=kernel,
        metric=metric,
        coordinate_names=support.coordinate_names,
        support_ids=support.ids,
        support_measure=support.measure,
        crs=support.crs,
        spatial_unit=support.spatial_unit,
        support_fingerprint=support.fingerprint,
        metadata={
            "support_shape": support.shape,
            "dimension": support.dimension,
            "boundary_correction": boundary_correction,
            "boundary_fingerprint": None,
        },
    )


def test_spatial_relative_risk_reciprocal_and_log_identity() -> None:
    support = _grid()
    case = _spatial_density(support, [0.2, 0.4, 0.8])
    control = _spatial_density(support, [0.4, 0.4, 0.4])

    risk = estimate_relative_risk(case, control, support=support)
    swapped = estimate_relative_risk(control, case, support=support)

    assert isinstance(risk, RelativeRiskField)
    assert np.allclose(risk.values, [0.5, 1.0, 2.0])
    assert np.allclose(risk.log_values, np.log([0.5, 1.0, 2.0]))
    assert np.allclose(swapped.values, 1.0 / risk.values)
    assert np.allclose(swapped.log_values, -risk.log_values)
    assert risk.case_integral == pytest.approx(1.0)
    assert risk.control_integral == pytest.approx(1.0)
    assert risk.effective_control_integral == pytest.approx(1.0)
    assert risk.control_weighted_mean == pytest.approx(1.0)
    assert risk.effective_control_weighted_mean == pytest.approx(1.0)
    assert risk.to_grid().shape == support.shape
    assert risk.log_to_grid().shape == support.shape
    assert not risk.values.flags.writeable
    assert not risk.log_values.flags.writeable
    assert (
        risk.fingerprint
        == estimate_relative_risk(
            case,
            control,
            support=support,
        ).fingerprint
    )


def test_control_denominator_policies_and_zero_case_log() -> None:
    support = _grid()
    case = _spatial_density(support, [0.0, 0.5, 1.0])
    control = _spatial_density(support, [0.6, 0.0, 0.8])

    with pytest.raises(ValueError, match="rejected 1 value"):
        estimate_relative_risk(case, control, support=support)

    nan_risk = estimate_relative_risk(
        case,
        control,
        support=support,
        zero_policy="nan",
    )
    assert nan_risk.values[0] == pytest.approx(0.0)
    assert np.isneginf(nan_risk.log_values[0])
    assert np.isnan(nan_risk.values[1])
    assert np.isnan(nan_risk.log_values[1])
    assert nan_risk.values[2] == pytest.approx(1.25)
    assert np.array_equal(nan_risk.invalid_mask, [False, True, False])
    assert not np.any(nan_risk.adjusted_mask)

    minimum_risk = estimate_relative_risk(
        case,
        control,
        support=support,
        zero_policy="minimum",
        minimum_denominator=0.25,
    )
    assert np.allclose(minimum_risk.effective_control_density, [0.6, 0.25, 0.8])
    assert np.allclose(minimum_risk.values, [0.0, 2.0, 1.25])
    assert np.isneginf(minimum_risk.log_values[0])
    assert np.array_equal(minimum_risk.invalid_mask, [False, True, False])
    assert np.array_equal(minimum_risk.adjusted_mask, [False, True, False])
    assert minimum_risk.metadata["adjusted_control_count"] == 1
    frame = minimum_risk.to_frame()
    assert frame["invalid_control_density"].sum() == 1
    assert frame["adjusted_control_density"].sum() == 1


def test_density_target_normalization_and_fixed_bandwidth_are_required() -> None:
    support = _grid()
    valid = _spatial_density(support, [0.4, 0.4, 0.4])

    with pytest.raises(ValueError, match="target='density'"):
        estimate_relative_risk(
            _spatial_density(
                support,
                [0.4, 0.4, 0.4],
                target="intensity",
            ),
            valid,
            support=support,
        )

    with pytest.raises(ValueError, match="integrate to one"):
        estimate_relative_risk(
            _spatial_density(support, [0.2, 0.2, 0.2]),
            valid,
            support=support,
        )

    with pytest.raises(ValueError, match="fixed scalar"):
        estimate_relative_risk(
            _spatial_density(
                support,
                [0.4, 0.4, 0.4],
                bandwidth=np.ones(3),
            ),
            valid,
            support=support,
        )


def test_spatial_support_is_explicit_and_contract_mismatch_is_rejected() -> None:
    support = _grid()
    case = _spatial_density(support, [0.2, 0.4, 0.8])
    control = _spatial_density(support, [0.4, 0.4, 0.4])

    with pytest.raises(ValueError, match="support=GridSupport"):
        estimate_relative_risk(case, control)

    with pytest.raises(ValueError, match="same fixed bandwidths"):
        estimate_relative_risk(
            case,
            _spatial_density(
                support,
                [0.4, 0.4, 0.4],
                bandwidth=2.0,
            ),
            support=support,
        )

    with pytest.raises(ValueError, match="estimator contracts differ"):
        estimate_relative_risk(
            case,
            _spatial_density(
                support,
                [0.4, 0.4, 0.4],
                kernel="epanechnikov",
            ),
            support=support,
        )

    other = GridSupport.from_bounds(
        (1.0, 0.0, 3.5, 1.0),
        resolution=1.0,
        crs="EPSG:3857",
        spatial_unit="m",
    )
    with pytest.raises(ValueError, match="support fingerprints"):
        estimate_relative_risk(case, control, support=other)


def test_normalization_tolerance_is_explicit() -> None:
    support = _grid()
    nearly_normalized = _spatial_density(
        support,
        [0.4000002, 0.4, 0.4],
    )
    control = _spatial_density(support, [0.4, 0.4, 0.4])

    risk = estimate_relative_risk(
        nearly_normalized,
        control,
        support=support,
        normalization_tolerance=1e-6,
    )
    assert risk.case_integral == pytest.approx(1.0000002)

    with pytest.raises(ValueError, match="normalization_tolerance"):
        estimate_relative_risk(
            nearly_normalized,
            control,
            support=support,
            normalization_tolerance=1e-8,
        )


def test_network_lixel_relative_risk_infers_support() -> None:
    dataset = load_t_junction()
    lixels = LixelSupport.from_network(dataset.network, length=0.4)
    density = 1.0 / float(np.sum(lixels.measure))
    case = NetworkField(
        values=np.full(lixels.n_lixels, density),
        support=lixels,
        bandwidth=0.8,
        target="density",
        kernel="gaussian",
        junction_policy="continuous",
        directed=False,
        network_fingerprint=dataset.network.fingerprint,
        event_fingerprint="case-events",
        metadata={"path_based": True, "n_events": 5},
    )
    control = NetworkField(
        values=np.full(lixels.n_lixels, density),
        support=lixels,
        bandwidth=0.8,
        target="density",
        kernel="gaussian",
        junction_policy="continuous",
        directed=False,
        network_fingerprint=dataset.network.fingerprint,
        event_fingerprint="control-events",
        metadata={"path_based": True, "n_events": 9},
    )

    risk = estimate_relative_risk(case, control)

    assert np.allclose(risk.values, 1.0)
    assert np.allclose(risk.log_values, 0.0)
    assert risk.descriptor.kind == "network_lixel"
    assert risk.result_family == "network"
    assert risk.metadata["case_source_metadata"]["n_events"] == 5
    assert risk.metadata["control_source_metadata"]["n_events"] == 9


def test_cyclic_spatiotemporal_grid_relative_risk() -> None:
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
    density = 1.0 / float(np.sum(support.measure))
    case = SpatiotemporalKDEResult(
        values=np.full(support.n_points, density),
        support=support,
        spatial_bandwidth=1.0,
        temporal_bandwidth=0.5,
        target="density",
        spatial_kernel="gaussian",
        temporal_kernel="gaussian",
        spatial_metric="euclidean",
        metadata={"n_events": 4},
    )
    control = SpatiotemporalKDEResult(
        values=np.full(support.n_points, density),
        support=support,
        spatial_bandwidth=1.0,
        temporal_bandwidth=0.5,
        target="density",
        spatial_kernel="gaussian",
        temporal_kernel="gaussian",
        spatial_metric="euclidean",
        metadata={"n_events": 7},
    )

    risk = estimate_relative_risk(case, control)

    assert np.allclose(risk.values, 1.0)
    assert risk.descriptor.kind == "spatiotemporal_grid"
    assert risk.descriptor.time_domain_fingerprint == support.time_domain.fingerprint
    assert risk.to_grid().shape == support.shape


def test_cyclic_network_time_arixel_relative_risk() -> None:
    dataset = load_t_junction()
    lixels = LixelSupport.from_network(dataset.network, length=0.5)
    support = ArixelSupport.from_lixels(
        lixels,
        temporal_resolution=1.0,
        temporal_unit="hour",
        time_domain=CyclicTimeDomain(period=2.0),
    )
    density = 1.0 / float(np.sum(support.measure))
    case = NetworkTimeField(
        values=np.full(support.n_arixels, density),
        support=support,
        spatial_bandwidth=0.8,
        temporal_bandwidth=0.5,
        target="density",
        spatial_kernel="gaussian",
        temporal_kernel="gaussian",
        junction_policy="continuous",
        directed=False,
        network_fingerprint=dataset.network.fingerprint,
        event_fingerprint="case-network-time-events",
        metadata={"n_events": 3},
    )
    control = NetworkTimeField(
        values=np.full(support.n_arixels, density),
        support=support,
        spatial_bandwidth=0.8,
        temporal_bandwidth=0.5,
        target="density",
        spatial_kernel="gaussian",
        temporal_kernel="gaussian",
        junction_policy="continuous",
        directed=False,
        network_fingerprint=dataset.network.fingerprint,
        event_fingerprint="control-network-time-events",
        metadata={"n_events": 8},
    )

    risk = estimate_relative_risk(case, control)

    assert np.allclose(risk.values, 1.0)
    assert risk.descriptor.kind == "network_time_arixel"
    assert risk.descriptor.time_domain_fingerprint == support.time_domain.fingerprint
    assert risk.to_grid().shape == support.shape
