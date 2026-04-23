# maxframe.dataframe.Series.nlargest

#### Series.nlargest(n, keep='first')

Return the largest n elements.

* **Parameters:**
  * **n** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *default 5*) – Return this many descending sorted values.
  * **keep** ( *{'first'* *,*  *'last'* *,*  *'all'}* *,* *default 'first'*) – 

    When there are duplicate values that cannot all fit in a
    Series of n elements:
    - `first`
      : of appearance.
    - `last`
      : order of appearance.
    - `all`
      : size larger than n.
* **Returns:**
  The n largest values in the Series, sorted in decreasing order.
* **Return type:**
  [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series)

#### SEE ALSO
[`Series.nsmallest`](maxframe.dataframe.Series.nsmallest.md#maxframe.dataframe.Series.nsmallest)
: Get the n smallest elements.

[`Series.sort_values`](maxframe.dataframe.Series.sort_values.md#maxframe.dataframe.Series.sort_values)
: Sort Series by values.

[`Series.head`](maxframe.dataframe.Series.head.md#maxframe.dataframe.Series.head)
: Return the first n rows.

### Notes

Faster than `.sort_values(ascending=False).head(n)` for small n
relative to the size of the `Series` object.

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> countries_population = {"Italy": 59000000, "France": 65000000,
...                         "Malta": 434000, "Maldives": 434000,
...                         "Brunei": 434000, "Iceland": 337000,
...                         "Nauru": 11300, "Tuvalu": 11300,
...                         "Anguilla": 11300, "Montserrat": 5200}
>>> s = md.Series(countries_population)
>>> s.execute()
Italy       59000000
France      65000000
Malta         434000
Maldives      434000
Brunei        434000
Iceland       337000
Nauru          11300
Tuvalu         11300
Anguilla       11300
Montserrat      5200
dtype: int64
```

The n largest elements where `n=5` by default.

```pycon
>>> s.nlargest().execute()
France      65000000
Italy       59000000
Malta         434000
Maldives      434000
Brunei        434000
dtype: int64
```

The n largest elements where `n=3`. Default keep value is ‘first’
so Malta will be kept.

```pycon
>>> s.nlargest(3).execute()
France    65000000
Italy     59000000
Malta       434000
dtype: int64
```

The n largest elements where `n=3` and keeping the last duplicates.
Brunei will be kept since it is the last with value 434000 based on
the index order.

```pycon
>>> s.nlargest(3, keep='last').execute()
France      65000000
Italy       59000000
Brunei        434000
dtype: int64
```

The n largest elements where `n=3` with all duplicates kept. Note
that the returned Series has five elements due to the three duplicates.

```pycon
>>> s.nlargest(3, keep='all').execute()
France      65000000
Italy       59000000
Malta         434000
Maldives      434000
Brunei        434000
dtype: int64
```
