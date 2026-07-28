# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Compute exposure-adjusted event rates and case-control relative risk."""

from __future__ import annotations

import numpy as np

from pykdex import (
    EventRateField,
    ExposureField,
    GridSupport,
    RelativeRiskField,
    SpatialKDEResult,
    estimate_event_rate,
    estimate_relative_risk,
)


def spatial_result(
    values: list[float],
    *,
    target: str,
    sample: str,
    support: GridSupport,
) -> SpatialKDEResult:
    """Create a measured spatial result with an explicit shared KDE contract."""
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
        metadata={
            "support_shape": support.shape,
            "dimension": support.dimension,
            "boundary_correction": "none",
            "boundary_fingerprint": None,
            "sample": sample,
        },
    )


# The final cell is half as wide as the first two, so all integrations use the
# actual per-cell measure rather than assuming equal cells.
grid = GridSupport.from_bounds(
    (0.0, 0.0, 2.5, 1.0),
    resolution=1.0,
    crs="EPSG:3857",
    spatial_unit="m",
)

exposure = ExposureField.from_amounts(
    [100.0, 50.0, 25.0],
    grid,
    exposure_unit="persons",
    metadata={"source": "illustrative population"},
)
intensity = spatial_result(
    [4.0, 2.0, 0.0],
    target="intensity",
    sample="events",
    support=grid,
)
rate = estimate_event_rate(
    intensity,
    exposure,
    event_unit="events",
)

case_density = spatial_result(
    [0.2, 0.4, 0.8],
    target="density",
    sample="cases",
    support=grid,
)
control_density = spatial_result(
    [0.4, 0.4, 0.4],
    target="density",
    sample="controls",
    support=grid,
)
risk = estimate_relative_risk(
    case_density,
    control_density,
    support=grid,
)

assert isinstance(exposure, ExposureField)
assert isinstance(rate, EventRateField)
assert isinstance(risk, RelativeRiskField)
assert np.allclose(exposure.amounts, [100.0, 50.0, 25.0])
assert exposure.total_exposure == 175.0
assert np.allclose(rate.values, [0.04, 0.04, 0.0])
assert rate.rate_unit == "events/persons"
assert rate.event_mass == 6.0
assert np.allclose(risk.values, [0.5, 1.0, 2.0])
assert np.allclose(risk.log_values, np.log([0.5, 1.0, 2.0]))
assert risk.case_integral == 1.0
assert risk.control_integral == 1.0
assert risk.control_weighted_mean == 1.0

print(
    {
        "total_exposure": exposure.total_exposure,
        "event_mass": rate.event_mass,
        "event_rate": rate.values.tolist(),
        "relative_risk": risk.values.tolist(),
        "log_relative_risk": risk.log_values.tolist(),
    }
)
