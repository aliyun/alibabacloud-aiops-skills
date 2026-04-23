# maxframe.dataframe.DataFrame.rename

#### DataFrame.rename(mapper=None, index=None, columns=None, axis='index', copy=True, inplace=False, level=None, errors='ignore')

Alter axes labels.

Function / dict values must be unique (1-to-1). Labels not contained in
a dict / Series will be left as-is. Extra labels listed don’t throw an
error.

* **Parameters:**
  * **mapper** (*dict-like* *or* *function*) – Dict-like or functions transformations to apply to
    that axis’ values. Use either `mapper` and `axis` to
    specify the axis to target with `mapper`, or `index` and
    `columns`.
  * **index** (*dict-like* *or* *function*) – Alternative to specifying axis (`mapper, axis=0`
    is equivalent to `index=mapper`).
  * **columns** (*dict-like* *or* *function*) – Alternative to specifying axis (`mapper, axis=1`
    is equivalent to `columns=mapper`).
  * **axis** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*str*](https://docs.python.org/3/library/stdtypes.html#str)) – Axis to target with `mapper`. Can be either the axis name
    (‘index’, ‘columns’) or number (0, 1). The default is ‘index’.
  * **copy** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default True*) – Also copy underlying data.
  * **inplace** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default False*) – Whether to return a new DataFrame. If True then value of copy is
    ignored.
  * **level** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* *level name* *,* *default None*) – In case of a MultiIndex, only rename labels in the specified
    level.
  * **errors** ( *{'ignore'* *,*  *'raise'}* *,* *default 'ignore'*) – If ‘raise’, raise a KeyError when a dict-like mapper, index,
    or columns contains labels that are not present in the Index
    being transformed.
    If ‘ignore’, existing keys will be renamed and extra keys will be
    ignored.
* **Returns:**
  DataFrame with the renamed axis labels.
* **Return type:**
  [DataFrame](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame)
* **Raises:**
  [**KeyError**](https://docs.python.org/3/library/exceptions.html#KeyError) – If any of the labels is not found in the selected axis and
      “errors=’raise’”.

#### SEE ALSO
[`DataFrame.rename_axis`](maxframe.dataframe.DataFrame.rename_axis.md#maxframe.dataframe.DataFrame.rename_axis)
: Set the name of the axis.

### Examples

`DataFrame.rename` supports two calling conventions

* `(index=index_mapper, columns=columns_mapper, ...)`
* `(mapper, axis={'index', 'columns'}, ...)`

We *highly* recommend using keyword arguments to clarify your
intent.

Rename columns using a mapping:

```pycon
>>> import maxframe.dataframe as md
>>> df = md.DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]})
>>> df.rename(columns={"A": "a", "B": "c"}).execute()
   a  c
0  1  4
1  2  5
2  3  6
```

Rename index using a mapping:

```pycon
>>> df.rename(index={0: "x", 1: "y", 2: "z"}).execute()
   A  B
x  1  4
y  2  5
z  3  6
```

Cast index labels to a different type:

```pycon
>>> df.index.execute()
RangeIndex(start=0, stop=3, step=1)
>>> df.rename(index=str).index.execute()
Index(['0', '1', '2'], dtype='object')
```

```pycon
>>> df.rename(columns={"A": "a", "B": "b", "C": "c"}, errors="raise").execute()
Traceback (most recent call last):
KeyError: ['C'] not found in axis
```

Using axis-style parameters

```pycon
>>> df.rename(str.lower, axis='columns').execute()
   a  b
0  1  4
1  2  5
2  3  6
```

```pycon
>>> df.rename({1: 2, 2: 4}, axis='index').execute()
   A  B
0  1  4
2  2  5
4  3  6
```
