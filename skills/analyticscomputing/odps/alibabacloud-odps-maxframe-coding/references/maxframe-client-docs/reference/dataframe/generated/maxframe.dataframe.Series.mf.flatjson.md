# maxframe.dataframe.Series.mf.flatjson

#### Series.mf.flatjson(query_paths: [List](https://docs.python.org/3/library/typing.html#typing.List)[[str](https://docs.python.org/3/library/stdtypes.html#str)], dtypes=None, dtype=None, name: [str](https://docs.python.org/3/library/stdtypes.html#str) = None) → DataFrame

Flat JSON object in the series to a dataframe according to JSON query.

* **Parameters:**
  * **series** ([*Series*](maxframe.dataframe.Series.md#maxframe.dataframe.Series)) – The series of json strings.
  * **query_paths** (*List* *[*[*str*](https://docs.python.org/3/library/stdtypes.html#str) *] or* [*str*](https://docs.python.org/3/library/stdtypes.html#str)) – The JSON query paths for each generated column. The path format should follow
    [RFC9535]([https://datatracker.ietf.org/doc/rfc9535/](https://datatracker.ietf.org/doc/rfc9535/)).
  * **dtypes** ([*Series*](maxframe.dataframe.Series.md#maxframe.dataframe.Series) *,* *default None*) – Specify dtypes of returned DataFrame. Can’t work with dtype.
  * **dtype** ([*numpy.dtype*](https://numpy.org/doc/stable/reference/generated/numpy.dtype.html#numpy.dtype) *,* *default None*) – Specify dtype of returned Series. Can’t work with dtypes.
  * **name** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *default None*) – Specify name of the returned Series.
* **Returns:**
  Result of DataFrame when dtypes specified, else Series.
* **Return type:**
  [DataFrame](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame) or [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series)

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> import pandas as pd
>>> s = md.Series(
...     [
...         '{"age": 24, "gender": "male", "graduated": false}',
...         '{"age": 25, "gender": "female", "graduated": true}',
...     ]
... )
>>> s.execute()
0    {"age": 24, "gender": "male", "graduated": false}
1    {"age": 25, "gender": "female", "graduated": true}
dtype: object
```

```pycon
>>> df = s.mf.flatjson(
...    ["$.age", "$.gender", "$.graduated"],
...    dtypes=pd.Series(["int32", "object", "bool"], index=["age", "gender", "graduated"]),
... )
>>> df.execute()
    age  gender  graduated
0   24    male       True
1   25  female       True
```

```pycon
>>> s2 = s.mf.flatjson("$.age", name="age", dtype="int32")
>>> s2.execute()
0    24
1    25
Name: age, dtype: int32
```
