# maxframe.dataframe.Series.set_axis

#### Series.set_axis(labels, axis=0, inplace=False)

Assign desired index to given axis.

Indexes for row labels can be changed by assigning
a list-like or Index.

* **Parameters:**
  * **labels** (*list-like* *,* [*Index*](maxframe.dataframe.Index.md#maxframe.dataframe.Index)) – The values for the new index.
  * **axis** ( *{0* *or*  *'index'}* *,* *default 0*) – The axis to update. The value 0 identifies the rows.
  * **inplace** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default False*) – Whether to return a new Series instance.
* **Returns:**
  **renamed** – An object of type Series or None if `inplace=True`.
* **Return type:**
  [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series) or None

#### SEE ALSO
`Series.rename_axis`
: Alter the name of the index.

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> s = md.Series([1, 2, 3])
>>> s.execute()
0    1
1    2
2    3
dtype: int64
```

```pycon
>>> s.set_axis(['a', 'b', 'c'], axis=0).execute()
a    1
b    2
c    3
dtype: int64
```
