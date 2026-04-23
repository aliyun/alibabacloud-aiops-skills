# maxframe.dataframe.DataFrame.applymap

#### DataFrame.applymap(func, na_action=None, dtypes=None, dtype=None, skip_infer=False, \*\*kwargs)

Apply a function to a Dataframe elementwise.

This method applies a function that accepts and returns a scalar
to every element of a DataFrame.

* **Parameters:**
  * **func** (*callable*) – Python function, returns a single value from a single value.
  * **na_action** ( *{None* *,*  *'ignore'}* *,* *default None*) – If ‘ignore’, propagate NaN values, without passing them to func.
  * **dtypes** ([*Series*](maxframe.dataframe.Series.md#maxframe.dataframe.Series) *,* *default None*) – Specify dtypes of returned DataFrames.
  * **dtype** (*np.dtype* *,* *default None*) – Specify dtypes of all columns of returned DataFrames, only
    effective when dtypes is not specified.
  * **skip_infer** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default False*) – Whether infer dtypes when dtypes or dtype is not specified.
  * **\*\*kwargs** – Additional keyword arguments to pass as keywords arguments to
    func.
* **Returns:**
  Transformed DataFrame.
* **Return type:**
  [DataFrame](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame)

#### SEE ALSO
[`DataFrame.apply`](maxframe.dataframe.DataFrame.apply.md#maxframe.dataframe.DataFrame.apply)
: Apply a function along input axis of DataFrame.

`DataFrame.replace`
: Replace values given in to_replace with value.

[`Series.map`](maxframe.dataframe.Series.map.md#maxframe.dataframe.Series.map)
: Apply a function elementwise on a Series.

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> df = md.DataFrame([[1, 2.12], [3.356, 4.567]])
>>> df.execute()
       0      1
0  1.000  2.120
1  3.356  4.567
```

```pycon
>>> df.map(lambda x: len(str(x))).execute()
   0  1
0  3  4
1  5  5
```

Like Series.map, NA values can be ignored:

```pycon
>>> df_copy = df.copy()
>>> df_copy.iloc[0, 0] = md.NA
>>> df_copy.map(lambda x: len(str(x)), na_action='ignore').execute()
     0  1
0  NaN  4
1  5.0  5
```

It is also possible to use map with functions that are not
lambda functions:

```pycon
>>> df.map(round, ndigits=1).execute()
     0    1
0  1.0  2.1
1  3.4  4.6
```

Note that a vectorized version of func often exists, which will
be much faster. You could square each number elementwise.

```pycon
>>> df.map(lambda x: x**2).execute()
           0          1
0   1.000000   4.494400
1  11.262736  20.857489
```

But it’s better to avoid map in that case.

```pycon
>>> (df ** 2).execute()
           0          1
0   1.000000   4.494400
1  11.262736  20.857489
```
