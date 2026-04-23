# maxframe.dataframe.Series.rename

#### Series.rename(index=None, , axis='index', copy=True, inplace=False, level=None, errors='ignore')

Alter Series index labels or name.

Function / dict values must be unique (1-to-1). Labels not contained in
a dict / Series will be left as-is. Extra labels listed don’t throw an
error.

Alternatively, change `Series.name` with a scalar value.

* **Parameters:**
  * **axis** ( *{0* *or*  *"index"}*) – Unused. Accepted for compatibility with DataFrame method only.
  * **index** (*scalar* *,* *hashable sequence* *,* *dict-like* *or* *function* *,* *optional*) – Functions or dict-like are transformations to apply to
    the index.
    Scalar or hashable sequence-like will alter the `Series.name`
    attribute.
  * **\*\*kwargs** – Additional keyword arguments passed to the function. Only the
    “inplace” keyword is used.
* **Returns:**
  Series with index labels or name altered.
* **Return type:**
  [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series)

#### SEE ALSO
[`DataFrame.rename`](maxframe.dataframe.DataFrame.rename.md#maxframe.dataframe.DataFrame.rename)
: Corresponding DataFrame method.

`Series.rename_axis`
: Set the name of the axis.

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> s = md.Series([1, 2, 3])
>>> s.execute()
0    1
1    2
2    3
dtype: int64
>>> s.rename("my_name").execute()  # scalar, changes Series.name.execute()
0    1
1    2
2    3
Name: my_name, dtype: int64
>>> s.rename({1: 3, 2: 5}).execute()  # mapping, changes labels.execute()
0    1
3    2
5    3
dtype: int64
```
