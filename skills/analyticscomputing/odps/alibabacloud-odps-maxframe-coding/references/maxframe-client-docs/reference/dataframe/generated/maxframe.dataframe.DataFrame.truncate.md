# maxframe.dataframe.DataFrame.truncate

#### DataFrame.truncate(before=None, after=None, axis=0, copy=None)

Truncate a Series or DataFrame before and after some index value.

This is a useful shorthand for boolean indexing based on index
values above or below certain thresholds.

* **Parameters:**
  * **before** (*date* *,* [*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* [*int*](https://docs.python.org/3/library/functions.html#int)) – Truncate all rows before this index value.
  * **after** (*date* *,* [*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* [*int*](https://docs.python.org/3/library/functions.html#int)) – Truncate all rows after this index value.
  * **axis** ( *{0* *or*  *'index'* *,* *1* *or*  *'columns'}* *,* *optional*) – Axis to truncate. Truncates the index (rows) by default.
    For Series this parameter is unused and defaults to 0.
  * **copy** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default is True* *,*) – This parameter is only kept for compatibility with pandas.
* **Returns:**
  The truncated Series or DataFrame.
* **Return type:**
  [type](https://docs.python.org/3/library/functions.html#type) of caller

#### SEE ALSO
[`DataFrame.loc`](maxframe.dataframe.DataFrame.loc.md#maxframe.dataframe.DataFrame.loc)
: Select a subset of a DataFrame by label.

[`DataFrame.iloc`](maxframe.dataframe.DataFrame.iloc.md#maxframe.dataframe.DataFrame.iloc)
: Select a subset of a DataFrame by position.

### Notes

If the index being truncated contains only datetime values,
before and after may be specified as strings instead of
Timestamps.

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> df = md.DataFrame({'A': ['a', 'b', 'c', 'd', 'e'],
...                    'B': ['f', 'g', 'h', 'i', 'j'],
...                    'C': ['k', 'l', 'm', 'n', 'o']},
...                   index=[1, 2, 3, 4, 5])
>>> df.execute()
   A  B  C
1  a  f  k
2  b  g  l
3  c  h  m
4  d  i  n
5  e  j  o
```

```pycon
>>> df.truncate(before=2, after=4).execute()
   A  B  C
2  b  g  l
3  c  h  m
4  d  i  n
```

The columns of a DataFrame can be truncated.

```pycon
>>> df.truncate(before="A", after="B", axis="columns").execute()
   A  B
1  a  f
2  b  g
3  c  h
4  d  i
5  e  j
```

For Series, only rows can be truncated.

```pycon
>>> df['A'].truncate(before=2, after=4).execute()
2    b
3    c
4    d
Name: A, dtype: object
```

The index values in `truncate` can be datetimes or string
dates.

```pycon
>>> dates = md.date_range('2016-01-01', '2016-02-01', freq='s')
>>> df = md.DataFrame(index=dates, data={'A': 1})
>>> df.tail().execute()
                     A
2016-01-31 23:59:56  1
2016-01-31 23:59:57  1
2016-01-31 23:59:58  1
2016-01-31 23:59:59  1
2016-02-01 00:00:00  1
```

```pycon
>>> df.truncate(before=md.Timestamp('2016-01-05'),
...             after=md.Timestamp('2016-01-10')).tail().execute()
                     A
2016-01-09 23:59:56  1
2016-01-09 23:59:57  1
2016-01-09 23:59:58  1
2016-01-09 23:59:59  1
2016-01-10 00:00:00  1
```

Because the index is a DatetimeIndex containing only dates, we can
specify before and after as strings. They will be coerced to
Timestamps before truncation.

```pycon
>>> df.truncate('2016-01-05', '2016-01-10').tail().execute()
                     A
2016-01-09 23:59:56  1
2016-01-09 23:59:57  1
2016-01-09 23:59:58  1
2016-01-09 23:59:59  1
2016-01-10 00:00:00  1
```

Note that `truncate` assumes a 0 value for any unspecified time
component (midnight). This differs from partial string slicing, which
returns any partially matching dates.

```pycon
>>> df.loc['2016-01-05':'2016-01-10', :].tail().execute()
                     A
2016-01-10 23:59:55  1
2016-01-10 23:59:56  1
2016-01-10 23:59:57  1
2016-01-10 23:59:58  1
2016-01-10 23:59:59  1
```
