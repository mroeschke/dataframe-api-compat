from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

from tests.utils import convert_series_to_pandas_numpy
from tests.utils import integer_series_1
from tests.utils import interchange_to_pandas

if TYPE_CHECKING:
    import pytest


def test_column_get_rows(library: str, request: pytest.FixtureRequest) -> None:
    ser = integer_series_1(library, request)
    namespace = ser.__column_namespace__()
    indices = namespace.column_from_sequence(
        [0, 2, 1], dtype=namespace.Int64(), name="result"
    )
    result = namespace.dataframe_from_dict(
        {"result": (ser.get_rows(indices)).rename("result")}
    )
    result_pd = interchange_to_pandas(result, library)["result"]
    result_pd = convert_series_to_pandas_numpy(result_pd)
    expected = pd.Series([1, 3, 2], name="result")
    pd.testing.assert_series_equal(result_pd, expected)
