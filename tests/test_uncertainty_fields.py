# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

from __future__ import annotations

import numpy as np
import pytest

from pykdex import GridSupport
from pykdex.uncertainty import (
    FieldEnsemble,
    PointwiseInterval,
    pointwise_percentile_interval,
)


def _grid() -> GridSupport:
    return GridSupport.from_bounds(
        (0.0, 0.0, 2.0, 1.0),
        resolution=1.0,
        spatial_unit="m",
    )


def _ensemble(**overrides: object) -> FieldEnsemble:
    values: dict[str, object] = {
        "replicate_values": np.array([[1.0, 2.0], [2.0, 4.0], [3.0, 6.0]]),
        "observed_values": np.array([2.0, 4.0]),
        "support": _grid(),
        "field_family": "density",
        "observed_field_fingerprint": "observed",
        "replicate_source_fingerprints": ("r0", "r1", "r2"),
        "resampling_method": "ordinary",
        "seed_ledger_fingerprint": "seeds",
        "execution_metadata": {"parallel_axis": "replicates"},
    }
    values.update(overrides)
    return FieldEnsemble(**values)  # type: ignore[arg-type]


def test_field_ensemble_is_exact_support_read_only_and_fingerprinted() -> None:
    ensemble = _ensemble()
    duplicate = _ensemble()

    assert ensemble.n_replicates == 3
    assert ensemble.n_elements == 2
    assert ensemble.descriptor.fingerprint == _grid().fingerprint
    assert ensemble.memory_bytes == 3 * 2 * 8 + 2 * 8 + 2
    assert ensemble.fingerprint == duplicate.fingerprint
    assert ensemble.execution_metadata["parallel_axis"] == "replicates"
    with pytest.raises(ValueError):
        ensemble.replicate_values[0, 0] = 0.0
    with pytest.raises(TypeError):
        ensemble.execution_metadata["parallel_axis"] = "none"  # type: ignore[index]


def test_pointwise_percentile_summary_matches_empirical_values() -> None:
    interval = pointwise_percentile_interval(
        _ensemble(),
        confidence_level=0.5,
    )

    assert isinstance(interval, PointwiseInterval)
    np.testing.assert_allclose(interval.lower, [1.5, 3.0])
    np.testing.assert_allclose(interval.estimate, [2.0, 4.0])
    np.testing.assert_allclose(interval.upper, [2.5, 5.0])
    np.testing.assert_allclose(interval.standard_error, [1.0, 2.0])
    np.testing.assert_allclose(interval.bias, [0.0, 0.0])
    assert interval.method == "percentile"
    assert interval.confidence_level == pytest.approx(0.5)
    assert interval.source_ensemble_fingerprint == _ensemble().fingerprint


def test_nan_validity_contract_is_shared_by_observed_and_all_replicates() -> None:
    ensemble = _ensemble(
        replicate_values=np.array([[1.0, np.nan], [2.0, np.nan], [3.0, np.nan]]),
        observed_values=np.array([2.0, np.nan]),
        valid_mask=np.array([True, False]),
    )
    interval = pointwise_percentile_interval(ensemble)

    assert np.all(np.isnan(interval.lower[1:]))
    assert np.all(np.isnan(interval.estimate[1:]))
    assert np.all(np.isnan(interval.standard_error[1:]))
    assert bool(interval.valid_mask[0])
    assert not bool(interval.valid_mask[1])


@pytest.mark.parametrize(
    "overrides",
    [
        {"replicate_values": np.ones((1, 2)), "replicate_source_fingerprints": ("r0",)},
        {"replicate_values": np.ones((3, 3))},
        {"observed_values": np.ones(3)},
        {"replicate_values": np.array([[1.0, np.nan], [2.0, 4.0], [3.0, 6.0]])},
        {
            "replicate_values": np.array(
                [[1.0, np.nan], [2.0, np.nan], [3.0, np.nan]]
            ),
            "observed_values": np.array([2.0, 4.0]),
            "valid_mask": np.array([True, False]),
        },
        {"replicate_values": np.array([[1.0, np.inf], [2.0, 4.0], [3.0, 6.0]])},
        {"replicate_values": np.array([[-1.0, 2.0], [2.0, 4.0], [3.0, 6.0]])},
        {"field_family": "unknown"},
        {"replicate_source_fingerprints": ("r0", "r1")},
        {"resampling_method": "bayesian"},
    ],
)
def test_field_ensemble_rejects_invalid_contracts(overrides: dict[str, object]) -> None:
    with pytest.raises((TypeError, ValueError)):
        _ensemble(**overrides)


def test_log_relative_risk_allows_negative_infinity_without_positive_infinity() -> None:
    ensemble = _ensemble(
        replicate_values=np.array(
            [[-np.inf, 0.0], [-np.inf, 0.5], [0.0, 1.0]]
        ),
        observed_values=np.array([-np.inf, 0.5]),
        field_family="log_relative_risk",
    )

    assert np.isneginf(ensemble.replicate_values[0, 0])
    with pytest.raises(ValueError, match="positive infinity"):
        _ensemble(
            replicate_values=np.array(
                [[np.inf, 0.0], [0.0, 0.5], [1.0, 1.0]]
            ),
            observed_values=np.array([0.0, 0.5]),
            field_family="log_relative_risk",
        )


def test_pointwise_log_interval_uses_empirical_order_for_negative_infinity() -> None:
    ensemble = _ensemble(
        replicate_values=np.array(
            [[-np.inf, 0.0], [-np.inf, 0.5], [0.0, 1.0]]
        ),
        observed_values=np.array([-np.inf, 0.5]),
        field_family="log_relative_risk",
    )
    interval = pointwise_percentile_interval(ensemble, confidence_level=0.5)

    assert np.isneginf(interval.lower[0])
    assert interval.upper[0] == pytest.approx(0.0)
    assert np.isnan(interval.standard_error[0])
    assert np.isnan(interval.bias[0])
    assert interval.standard_error[1] == pytest.approx(0.5)


def test_interval_rejects_wrong_support_length_and_invalid_level() -> None:
    with pytest.raises(ValueError, match="one value per support element"):
        PointwiseInterval(
            lower=np.ones(3),
            estimate=np.ones(3),
            upper=np.ones(3),
            standard_error=np.ones(3),
            bias=np.zeros(3),
            support=_grid(),
            field_family="density",
            confidence_level=0.95,
            source_ensemble_fingerprint="ensemble",
        )
    with pytest.raises(ValueError, match="lie in"):
        pointwise_percentile_interval(_ensemble(), confidence_level=1.0)
