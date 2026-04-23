# maxframe.dataframe.Series.mf.flatmap

#### Series.mf.flatmap(func: [Callable](https://docs.python.org/3/library/typing.html#typing.Callable), dtypes=None, dtype=None, name=None, args=(), \*\*kwargs)

Apply the given function to each row and then flatten results. Use this method if your transformation returns
multiple rows for each input row.

This function applies a transformation to each element of the Series, where the transformation can return zero
: or multiple values, effectively flattening Python generator, list-liked collections and DataFrame.

* **Parameters:**
  * **func** (*Callable*) – Function to apply to each element of the Series. It should accept a scalar value
    (or an array if `raw=True`) and return a list or iterable of values.
  * **dtypes** ([*Series*](maxframe.dataframe.Series.md#maxframe.dataframe.Series) *,* *default None*) – Specify dtypes of returned DataFrame. Can’t work with dtype.
  * **dtype** ([*numpy.dtype*](https://numpy.org/doc/stable/reference/generated/numpy.dtype.html#numpy.dtype) *,* *default None*) – Specify dtype of returned Series. Can’t work with dtypes.
  * **name** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *default None*) – Specify name of the returned Series.
  * **args** ([*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple)) – Positional arguments to pass to `func`.
  * **\*\*kwargs** – Additional keyword arguments to pass as keywords arguments to `func`.
* **Returns:**
  Result of DataFrame when dtypes specified, else Series.
* **Return type:**
  [DataFrame](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame) or [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series)

### Notes

The `func` must return an iterable of values for each input element. If `dtypes` is specified,
flatmap will return a DataFrame, if `dtype` and `name` is specified, a Series will be returned.

The index of the resulting DataFrame/Series will be repeated based on the number of output rows generated
by `func`.

### Examples

```pycon
>>> import numpy as np
>>> import maxframe.dataframe as md
>>> df = md.DataFrame({'A': [1, 2, 3], 'B': [4, 5, 6]})
>>> df.execute()
   A  B
0  1  4
1  2  5
2  3  6
```

Define a function that takes a number and returns a list of two numbers:

```pycon
>>> def generate_values_array(x):
...     return [x * 2, x * 3]
```

Specify `dtype` with a function which returns list to return more elements as a Series:

```pycon
>>> df['A'].mf.flatmap(generate_values_array, dtype="int", name="C").execute()
    0    2
    0    3
    1    4
    1    6
    2    6
    2    9
    Name: C, dtype: int64
```

Specify `dtypes` to return multi columns as a DataFrame:

```pycon
>>> def generate_values_in_generator(x):
...     yield pd.Series([x * 2, x * 4])
...     yield pd.Series([x * 3, x * 5])
```

```pycon
>>> df['A'].mf.flatmap(generate_values_in_generator, dtypes={"A": "int", "B": "int"}).execute()
       A   B
    0  2   4
    0  3   5
    1  4   8
    1  6  10
    2  6  12
    2  9  15
```
