# SPDX-FileCopyrightText: 2026 Jinghao Hu
# SPDX-License-Identifier: MIT

"""Built-in deterministic datasets and generators."""

from pykdex.datasets.synthetic import (
    load_bimodal_points,
    load_bounded_square,
    make_bimodal_events,
)

__all__ = ["make_bimodal_events", "load_bimodal_points", "load_bounded_square"]
