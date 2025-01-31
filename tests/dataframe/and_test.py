from __future__ import annotations

import pandas as pd
import pytest

from tests.utils import bool_dataframe_1
from tests.utils import bool_dataframe_4
from tests.utils import convert_dataframe_to_pandas_numpy
from tests.utils import interchange_to_pandas


def test_and(library: str, request: pytest.FixtureRequest) -> None:
    df = bool_dataframe_1(library)
    other = bool_dataframe_4(library)
    if library == "polars-lazy":
        with pytest.raises(NotImplementedError):
            result = df & other
        return
    else:
        result = df & other
    result_pd = interchange_to_pandas(result, library)
    result_pd = convert_dataframe_to_pandas_numpy(result_pd)
    expected = pd.DataFrame({"a": [False, True, False], "b": [True, True, True]})
    pd.testing.assert_frame_equal(result_pd, expected)


def test_and_with_scalar(library: str, request: pytest.FixtureRequest) -> None:
    df = bool_dataframe_1(library)
    other = True
    result = df & other
    result_pd = interchange_to_pandas(result, library)
    result_pd = convert_dataframe_to_pandas_numpy(result_pd)
    expected = pd.DataFrame({"a": [True, True, False], "b": [True, True, True]})
    pd.testing.assert_frame_equal(result_pd, expected)
