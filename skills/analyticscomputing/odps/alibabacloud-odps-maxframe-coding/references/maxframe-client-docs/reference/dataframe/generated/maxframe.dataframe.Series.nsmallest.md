# maxframe.dataframe.Series.nsmallest

#### Series.nsmallest(n, keep='first')

Return the smallest n elements.

* **Parameters:**
  * **n** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *default 5*) – Return this many ascending sorted values.
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
  The n smallest values in the Series, sorted in increasing order.
* **Return type:**
  [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series)

#### SEE ALSO
[`Series.nlargest`](maxframe.dataframe.Series.nlargest.md#maxframe.dataframe.Series.nlargest)
: Get the n largest elements.

[`Series.sort_values`](maxframe.dataframe.Series.sort_values.md#maxframe.dataframe.Series.sort_values)
: Sort Series by values.

[`Series.head`](maxframe.dataframe.Series.head.md#maxframe.dataframe.Series.head)
: Return the first n rows.

### Notes

Faster than `.sort_values().head(n)` for small n relative to
the size of the `Series` object.

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> countries_population = {"Italy": 59000000, "France": 65000000,
...                         "Brunei": 434000, "Malta": 434000,
...                         "Maldives": 434000, "Iceland": 337000,
...                         "Nauru": 11300, "Tuvalu": 11300,
...                         "Anguilla": 11300, "Montserrat": 5200}
>>> s = md.Series(countries_population)
>>> s.execute()
Italy       59000000
France      65000000
Brunei        434000
Malta         434000
Maldives      434000
Iceland       337000
Nauru          11300
Tuvalu         11300
Anguilla       11300
Montserrat      5200
dtype: int64
```

The n smallest elements where `n=5` by default.

```pycon
>>> s.nsmallest().execute()
Montserrat    5200
Nauru        11300
Tuvalu       11300
Anguilla     11300
Iceland     337000
dtype: int64
```

The n smallest elements where `n=3`. Default keep value is
‘first’ so Nauru and Tuvalu will be kept.

```pycon
>>> s.nsmallest(3).execute()
Montserrat   5200
Nauru       11300
Tuvalu      11300
dtype: int64
```

The n smallest elements where `n=3` and keeping the last
duplicates. Anguilla and Tuvalu will be kept since they are the last
with value 11300 based on the index order.

```pycon
>>> s.nsmallest(3, keep='last').execute()
Montserrat   5200
Anguilla    11300
Tuvalu      11300
dtype: int64
```

The n smallest elements where `n=3` with all duplicates kept. Note
that the returned Series has four elements due to the three duplicates.

```pycon
>>> s.nsmallest(3, keep='all').execute()
Montserrat   5200
Nauru       11300
Tuvalu      11300
Anguilla    11300
dtype: int64
```
