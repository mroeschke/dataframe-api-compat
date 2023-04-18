from __future__ import annotations
import numpy as np

import pandas as pd
from pandas.api.types import is_extension_array_dtype
import collections
from typing import Sequence, Mapping, NoReturn, Type


class PandasColumn:
    def __init__(self, column: pd.Series) -> None:  # type: ignore[type-arg]
        self._series = column

    def __len__(self) -> int:
        return len(self._series)

    def __getitem__(self, row: int) -> object:
        return self._series.iloc[row]

    def __iter__(self) -> NoReturn:
        raise NotImplementedError()

    def __dlpack__(self) -> object:
        arr = self._series.to_numpy()
        return arr.__dlpack__()

    def unique(self) -> PandasColumn:
        return PandasColumn(pd.Series(self._series.unique()))

    def mean(self) -> float:
        return self._series.mean()

    @classmethod
    def from_array(cls, array: object, dtype: str) -> PandasColumn:
        return cls(pd.Series(array, dtype=dtype))

    def isnull(self) -> PandasColumn:
        if is_extension_array_dtype(self._series.dtype):
            return PandasColumn(self._series.isnull())
        else:
            return PandasColumn(pd.Series(np.array([False] * len(self))))

    def isnan(self) -> PandasColumn:
        return PandasColumn(self._series.isna())

    def any(self) -> bool:
        return self._series.any()

    def all(self) -> bool:
        return self._series.all()

    def to_iterable(self) -> object:
        return self._series.to_numpy()

    def __eq__(self, other: PandasColumn) -> PandasColumn:  # type: ignore[override]
        return PandasColumn(self._series == other)

    def __and__(self, other: PandasColumn) -> PandasColumn:
        return PandasColumn(self._series & other._series)

    def __invert__(self) -> PandasColumn:
        # TODO: validate booleanness
        return PandasColumn(~self._series)

    def max(self) -> object:
        return self._series.max()


class PandasGroupBy:
    def __init__(self, df: pd.DataFrame, keys: Sequence[str]) -> None:
        self.df = df
        self.grouped = df.groupby(list(keys), sort=False, as_index=False)
        self.keys = list(keys)

    def _validate_result(self, result: pd.DataFrame) -> None:
        failed_columns = self.df.columns.difference(result.columns)
        if len(failed_columns) > 0:
            raise RuntimeError(
                "Groupby operation could not be performed on columns "
                f"{failed_columns}. Please drop them before calling groupby."
            )

    def size(self) -> PandasColumn:
        return PandasColumn(self.df.groupby(self.keys, as_index=True).size())

    def any(self, skipna: bool = True) -> PandasDataFrame:
        if not (self.df.drop(columns=self.keys).dtypes == "bool").all():
            raise ValueError("Expected boolean types")
        result = self.grouped.any()
        self._validate_result(result)
        return PandasDataFrame(result)

    def all(self, skipna: bool = True) -> PandasDataFrame:
        if not (self.df.drop(columns=self.keys).dtypes == "bool").all():
            raise ValueError("Expected boolean types")
        result = self.grouped.all()
        self._validate_result(result)
        return PandasDataFrame(result)

    def min(self, skipna: bool = True) -> PandasDataFrame:
        result = self.grouped.min()
        self._validate_result(result)
        return PandasDataFrame(result)

    def max(self, skipna: bool = True) -> PandasDataFrame:
        result = self.grouped.max()
        self._validate_result(result)
        return PandasDataFrame(result)

    def sum(self, skipna: bool = True) -> PandasDataFrame:
        result = self.grouped.sum()
        self._validate_result(result)
        return PandasDataFrame(result)

    def prod(self, skipna: bool = True) -> PandasDataFrame:
        result = self.grouped.prod()
        self._validate_result(result)
        return PandasDataFrame(result)

    def median(self, skipna: bool = True) -> PandasDataFrame:
        result = self.grouped.median()
        self._validate_result(result)
        return PandasDataFrame(result)

    def mean(self, skipna: bool = True) -> PandasDataFrame:
        result = self.grouped.mean()
        self._validate_result(result)
        return PandasDataFrame(result)

    def std(self, skipna: bool = True) -> PandasDataFrame:
        result = self.grouped.std()
        self._validate_result(result)
        return PandasDataFrame(result)

    def var(self, skipna: bool = True) -> PandasDataFrame:
        result = self.grouped.var()
        self._validate_result(result)
        return PandasDataFrame(result)


class PandasDataFrame:
    # Not technically part of the standard

    def __init__(self, dataframe: pd.DataFrame) -> None:
        self._validate_columns(dataframe.columns)  # type: ignore[arg-type]
        if (
            isinstance(dataframe.index, pd.RangeIndex)
            and dataframe.index.start == 0  # type: ignore[comparison-overlap]
            and dataframe.index.step == 1  # type: ignore[comparison-overlap]
            and (
                dataframe.index.stop  # type: ignore[comparison-overlap]
                == len(dataframe) - 1
            )
        ):
            self._dataframe = dataframe
        else:
            self._dataframe = dataframe.reset_index(drop=True)

    def __len__(self) -> int:
        return self.shape()[0]

    def _validate_columns(self, columns: Sequence[str]) -> None:
        counter = collections.Counter(columns)
        for col, count in counter.items():
            if count > 1:
                raise ValueError(
                    f"Expected unique column names, got {col} {count} time(s)"
                )
        for col in columns:
            if not isinstance(col, str):
                raise TypeError(
                    f"Expected column names to be of type str, got {col} "
                    f"of type {type(col)}"
                )

    def _validate_index(self, index: pd.Index) -> None:
        pd.testing.assert_index_equal(self.dataframe.index, index)

    def _validate_comparand(self, other: PandasDataFrame) -> None:
        if isinstance(other, PandasDataFrame) and not (
            self.dataframe.index.equals(other.dataframe.index)
            and self.dataframe.shape == other.dataframe.shape
            and self.dataframe.columns.equals(other.dataframe.columns)
        ):
            raise ValueError(
                "Expected DataFrame with same length, matching columns, "
                "and matching index."
            )

    def _validate_booleanness(self) -> None:
        if not (self.dataframe.dtypes == "bool").all():
            raise NotImplementedError(
                "'any' can only be called on DataFrame " "where all dtypes are 'bool'"
            )

    @property
    def column_class(self) -> Type[PandasColumn]:
        return PandasColumn

    # In the standard

    @property
    def dataframe(self) -> pd.DataFrame:
        return self._dataframe

    def shape(self) -> tuple[int, int]:
        return self.dataframe.shape

    @classmethod
    def from_dict(cls, data: dict[str, PandasColumn]) -> PandasDataFrame:
        return cls(
            pd.DataFrame({label: column._series for label, column in data.items()})
        )

    def groupby(self, keys: Sequence[str]) -> PandasGroupBy:
        if not isinstance(keys, collections.abc.Sequence):
            raise TypeError(f"Expected sequence of strings, got: {type(keys)}")
        if isinstance(keys, str):
            raise TypeError("Expected sequence of strings, got: str")
        for key in keys:
            if key not in self.get_column_names():
                raise KeyError(f"key {key} not present in DataFrame's columns")
        return PandasGroupBy(self.dataframe, keys)

    def get_column_by_name(self, name: str) -> PandasColumn:
        if not isinstance(name, str):
            raise TypeError(f"Expected str, got: {type(name)}")
        return PandasColumn(self.dataframe.loc[:, name])

    def get_columns_by_name(self, names: Sequence[str]) -> PandasDataFrame:
        if isinstance(names, str):
            raise TypeError(f"Expected sequence of str, got {type(names)}")
        self._validate_columns(names)
        return PandasDataFrame(self.dataframe.loc[:, list(names)])

    def get_rows(self, indices: Sequence[int]) -> PandasDataFrame:
        if not isinstance(indices, collections.abc.Sequence):
            raise TypeError(f"Expected Sequence of int, got {type(indices)}")
        return PandasDataFrame(self.dataframe.iloc[list(indices), :])

    def slice_rows(self, start: int, stop: int, step: int) -> PandasDataFrame:
        return PandasDataFrame(self.dataframe.iloc[start:stop:step])

    def get_rows_by_mask(self, mask: PandasColumn) -> PandasDataFrame:
        series = mask._series
        self._validate_index(series.index)
        return PandasDataFrame(self.dataframe.loc[series, :])

    def insert(self, loc: int, label: str, value: PandasColumn) -> PandasDataFrame:
        series = value._series
        self._validate_index(series.index)
        before = self.dataframe.iloc[:, :loc]
        after = self.dataframe.iloc[:, loc:]
        to_insert = value._series.rename(label)
        return PandasDataFrame(pd.concat([before, to_insert, after], axis=1))

    def drop_column(self, label: str) -> PandasDataFrame:
        if not isinstance(label, str):
            raise TypeError(f"Expected str, got: {type(label)}")
        return PandasDataFrame(self.dataframe.drop(label, axis=1))

    def set_column(self, label: str, value: PandasColumn) -> PandasDataFrame:
        columns = self.get_column_names()
        if label in columns:
            idx: int = columns.index(label)
            return self.drop_column(label).insert(idx, label, value)
        return self.insert(len(columns), label, value)

    def rename_columns(self, mapping: Mapping[str, str]) -> PandasDataFrame:
        if not isinstance(mapping, collections.abc.Mapping):
            raise TypeError(f"Expected Mapping, got: {type(mapping)}")
        return PandasDataFrame(self.dataframe.rename(columns=mapping))

    def get_column_names(self) -> Sequence[str]:
        return self.dataframe.columns.tolist()

    def __iter__(self) -> NoReturn:
        raise NotImplementedError()

    def __eq__(self, other: PandasDataFrame) -> PandasDataFrame:  # type: ignore[override]
        self._validate_comparand(other)
        return PandasDataFrame(self.dataframe.__eq__(other.dataframe))

    def __ne__(self, other: PandasDataFrame) -> PandasDataFrame:  # type: ignore[override]
        self._validate_comparand(other)
        return PandasDataFrame((self.dataframe.__ne__(other.dataframe)))

    def __ge__(self, other: PandasDataFrame) -> PandasDataFrame:
        self._validate_comparand(other)
        return PandasDataFrame((self.dataframe.__ge__(other.dataframe)))

    def __gt__(self, other: PandasDataFrame) -> PandasDataFrame:
        self._validate_comparand(other)
        return PandasDataFrame((self.dataframe.__gt__(other.dataframe)))

    def __le__(self, other: PandasDataFrame) -> PandasDataFrame:
        self._validate_comparand(other)
        return PandasDataFrame((self.dataframe.__le__(other.dataframe)))

    def __lt__(self, other: PandasDataFrame) -> PandasDataFrame:
        self._validate_comparand(other)
        return PandasDataFrame((self.dataframe.__lt__(other.dataframe)))

    def __add__(self, other: PandasDataFrame) -> PandasDataFrame:
        self._validate_comparand(other)
        return PandasDataFrame((self.dataframe.__add__(other.dataframe)))

    def __sub__(self, other: PandasDataFrame) -> PandasDataFrame:
        self._validate_comparand(other)
        return PandasDataFrame((self.dataframe.__sub__(other.dataframe)))

    def __mul__(self, other: PandasDataFrame) -> PandasDataFrame:
        self._validate_comparand(other)
        return PandasDataFrame((self.dataframe.__mul__(other.dataframe)))

    def __truediv__(self, other: PandasDataFrame) -> PandasDataFrame:
        self._validate_comparand(other)
        return PandasDataFrame((self.dataframe.__truediv__(other.dataframe)))

    def __floordiv__(self, other: PandasDataFrame) -> PandasDataFrame:
        self._validate_comparand(other)
        return PandasDataFrame((self.dataframe.__floordiv__(other.dataframe)))

    def __pow__(self, other: PandasDataFrame) -> PandasDataFrame:
        self._validate_comparand(other)
        return PandasDataFrame((self.dataframe.__pow__(other.dataframe)))

    def __mod__(self, other: PandasDataFrame) -> PandasDataFrame:
        self._validate_comparand(other)
        return PandasDataFrame((self.dataframe.__mod__(other.dataframe)))

    def __divmod__(
        self, other: PandasDataFrame
    ) -> tuple[PandasDataFrame, PandasDataFrame]:
        self._validate_comparand(other)
        quotient, remainder = self.dataframe.__divmod__(other.dataframe)
        return PandasDataFrame(quotient), PandasDataFrame(remainder)

    def any(self) -> PandasDataFrame:
        self._validate_booleanness()
        return PandasDataFrame(self.dataframe.any().to_frame().T)

    def all(self) -> PandasDataFrame:
        self._validate_booleanness()
        return PandasDataFrame(self.dataframe.all().to_frame().T)

    def any_rowwise(self) -> PandasColumn:
        self._validate_booleanness()
        return PandasColumn(self.dataframe.any(axis=1))

    def all_rowwise(self) -> PandasColumn:
        self._validate_booleanness()
        return PandasColumn(self.dataframe.all(axis=1))

    def isnull(self) -> PandasDataFrame:
        result = []
        for column in self.dataframe.columns:
            if is_extension_array_dtype(self.dataframe[column].dtype):
                result.append(self.dataframe[column].isnull())
            else:
                result.append(pd.Series(np.array([False] * self.shape()[0]), name=column))
        return PandasDataFrame(pd.concat(result, axis=1))

    def isnan(self) -> PandasDataFrame:
        result = []
        for column in self.dataframe.columns:
            if is_extension_array_dtype(self.dataframe[column].dtype):
                result.append(
                    np.isnan(self.dataframe[column]).replace(pd.NA, False).astype(bool)
                )
            else:
                result.append(self.dataframe[column].isna())
        return PandasDataFrame(pd.concat(result, axis=1))

    def concat(self, other: Sequence[PandasDataFrame]) -> PandasDataFrame:
        for _other in other:
            if _other.dataframe.dtypes != self.dataframe.dtypes:
                raise ValueError("Expected matching columns")
        return PandasDataFrame(
            pd.concat(
                [self.dataframe, *[_other.dataframe for _other in other]],
                axis=0,
                ignore_index=True,
            )
        )

    def sorted_indices(self, keys: Sequence[str]) -> PandasColumn:
        df = self.dataframe.loc[:, list(keys)]
        return PandasColumn(df.sort_values(keys).index.to_series())
