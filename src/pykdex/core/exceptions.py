# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT


"""Package-specific exception classes."""


class NotFittedError(ValueError):
    """Raised when a fitted-only operation is requested before fitting."""
