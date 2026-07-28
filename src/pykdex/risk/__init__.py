# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Exposure-adjusted rate and relative-risk foundations."""

from pykdex.risk.exposure import ExposureField
from pykdex.risk.support import (
    MeasuredSupport,
    SupportDescriptor,
    describe_measured_support,
    require_same_measured_support,
)

__all__ = [
    "ExposureField",
    "MeasuredSupport",
    "SupportDescriptor",
    "describe_measured_support",
    "require_same_measured_support",
]
