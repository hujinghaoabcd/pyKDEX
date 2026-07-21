"""Tests for structured result exports."""

import numpy as np
import pandas as pd

from pykdex import SpatialKDE, SpatialKDEResult


def test_predict_result_preserves_dataframe_coordinate_names(events_2d):
    events = pd.DataFrame(events_2d, columns=["east", "north"])
    support = pd.DataFrame([[0.0, 0.0], [1.0, 1.0]], columns=["east", "north"])
    result = SpatialKDE(bandwidth=0.5).fit(events).predict_result(support)
    assert isinstance(result, SpatialKDEResult)
    assert result.coordinate_names == ("east", "north")
    assert list(result.to_frame().columns) == ["east", "north", "density"]


def test_geodataframe_export(events_2d):
    support = np.array([[0.0, 0.0], [1.0, 1.0]])
    result = SpatialKDE(bandwidth=0.5).fit(events_2d).predict_result(support)
    geoframe = result.to_geodataframe(crs="EPSG:3857")
    assert geoframe.crs.to_epsg() == 3857
    assert geoframe.geometry.geom_type.tolist() == ["Point", "Point"]
