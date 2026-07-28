# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Exposure-adjusted rate and relative-risk foundations."""

from pykdex.risk.exposure import ExposureField
from pykdex.risk.policies import DenominatorPolicy
from pykdex.risk.rate import EventRateField, estimate_event_rate
from pykdex.risk.relative_risk import RelativeRiskField, estimate_relative_risk
from pykdex.risk.support import (
    MeasuredSupport,
    SupportDescriptor,
    describe_measured_support,
    require_same_measured_support,
)

__all__ = [
    "ExposureField",
    "DenominatorPolicy",
    "EventRateField",
    "estimate_event_rate",
    "RelativeRiskField",
    "estimate_relative_risk",
    "MeasuredSupport",
    "SupportDescriptor",
    "describe_measured_support",
    "require_same_measured_support",
]
