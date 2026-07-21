# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Structured validation reports for pyKDEX data objects.

Author:
    Jinghao Hu
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping

import pandas as pd


@dataclass(frozen=True)
class DataIssue:
    """One validation issue with a stable machine-readable code."""

    severity: str
    code: str
    message: str
    context: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        severity = str(self.severity).strip().lower()
        if severity not in {"error", "warning"}:
            raise ValueError("severity must be either 'error' or 'warning'.")
        code = str(self.code).strip()
        message = str(self.message).strip()
        if not code or not message:
            raise ValueError("code and message must be non-empty strings.")
        object.__setattr__(self, "severity", severity)
        object.__setattr__(self, "code", code)
        object.__setattr__(self, "message", message)
        object.__setattr__(self, "context", MappingProxyType(dict(self.context)))


@dataclass(frozen=True)
class DataValidationReport:
    """Immutable collection of validation issues and descriptive statistics."""

    issues: tuple[DataIssue, ...] = ()
    statistics: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "issues", tuple(self.issues))
        object.__setattr__(self, "statistics", MappingProxyType(dict(self.statistics)))

    @property
    def valid(self) -> bool:
        """Whether the report contains no errors."""
        return not any(issue.severity == "error" for issue in self.issues)

    @property
    def errors(self) -> tuple[DataIssue, ...]:
        """Validation errors."""
        return tuple(issue for issue in self.issues if issue.severity == "error")

    @property
    def warnings(self) -> tuple[DataIssue, ...]:
        """Validation warnings."""
        return tuple(issue for issue in self.issues if issue.severity == "warning")

    def raise_for_errors(self) -> None:
        """Raise a concise ValueError when the report contains errors."""
        if self.valid:
            return
        details = "; ".join(f"{issue.code}: {issue.message}" for issue in self.errors)
        raise ValueError(f"Data validation failed: {details}")

    def combine(self, *reports: "DataValidationReport") -> "DataValidationReport":
        """Combine this report with additional reports."""
        issues = list(self.issues)
        statistics = dict(self.statistics)
        for report in reports:
            issues.extend(report.issues)
            statistics.update(report.statistics)
        return DataValidationReport(tuple(issues), statistics)

    def to_frame(self) -> pd.DataFrame:
        """Return issues as a DataFrame."""
        return pd.DataFrame(
            [
                {
                    "severity": issue.severity,
                    "code": issue.code,
                    "message": issue.message,
                    "context": dict(issue.context),
                }
                for issue in self.issues
            ],
            columns=["severity", "code", "message", "context"],
        )
