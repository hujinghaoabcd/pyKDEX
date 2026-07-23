# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

import numpy as np
import pytest

from pykdex import (
    SpatiotemporalBandwidthExperiment,
    SpatiotemporalEvents,
    build_spatiotemporal_distance_asset,
)


def _events() -> SpatiotemporalEvents:
    return SpatiotemporalEvents.from_arrays(
        [[0.0], [0.2], [3.0], [3.2]],
        [0.0, 0.2, 4.0, 4.2],
        weights=[1.0, 2.0, 1.0, 2.0],
        spatial_unit="km",
        temporal_unit="hours",
    )


def test_joint_bandwidth_experiment_is_deterministic_and_reuses_asset() -> None:
    events = _events()
    asset = build_spatiotemporal_distance_asset(events, events)
    experiment = SpatiotemporalBandwidthExperiment(
        [0.2, 1.0, 4.0],
        [0.2, 1.0, 5.0],
        mode="joint",
    )

    first = experiment.run(events, distance_asset=asset)
    second = experiment.run(events, distance_asset=asset)

    assert first.spatial_bandwidth == second.spatial_bandwidth
    assert first.temporal_bandwidth == second.temporal_bandwidth
    np.testing.assert_allclose(first.score_matrix, second.score_matrix)
    assert first.distance_asset_fingerprint == asset.fingerprint
    assert len(first.to_frame()) == 9


def test_separate_experiment_selects_marginal_pair_and_reports_joint_score() -> None:
    result = SpatiotemporalBandwidthExperiment(
        [0.2, 1.0, 4.0],
        [0.2, 1.0, 5.0],
        mode="separate",
    ).run(_events())

    spatial_index = int(
        np.flatnonzero(result.spatial_candidates == result.spatial_bandwidth)[0]
    )
    temporal_index = int(
        np.flatnonzero(result.temporal_candidates == result.temporal_bandwidth)[0]
    )
    assert result.score == result.score_matrix[spatial_index, temporal_index]
    assert result.mode == "separate"
    assert result.objective == "loo_likelihood"


def test_bandwidth_experiment_validates_candidates_and_loo_sample_size() -> None:
    with pytest.raises(ValueError, match="positive"):
        SpatiotemporalBandwidthExperiment([0.0], [1.0])
    with pytest.raises(ValueError, match="duplicates"):
        SpatiotemporalBandwidthExperiment([1.0, 1.0], [1.0])
    with pytest.raises(ValueError, match="at least two"):
        SpatiotemporalBandwidthExperiment([1.0], [1.0]).run(
            SpatiotemporalEvents.from_arrays([[0.0]], [0.0], temporal_unit="hours")
        )
