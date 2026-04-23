# maxframe.dataframe.DataFrame.nlargest

#### DataFrame.nlargest(n, columns, keep='first')

Return the first n rows ordered by columns in descending order.

Return the first n rows with the largest values in columns, in
descending order. The columns that are not specified are returned as
well, but not used for ordering.

This method is equivalent to
`df.sort_values(columns, ascending=False).head(n)`, but more
performant.

* **Parameters:**
  * **n** ([*int*](https://docs.python.org/3/library/functions.html#int)) – Number of rows to return.
  * **columns** (*label* *or* [*list*](https://docs.python.org/3/library/stdtypes.html#list) *of* *labels*) – Column label(s) to order by.
  * **keep** ( *{'first'* *,*  *'last'* *,*  *'all'}* *,* *default 'first'*) – 

    Where there are duplicate values:
    - first : prioritize the first occurrence(s)
    - last : prioritize the last occurrence(s)
    - `all`
      : selecting more than n items.
* **Returns:**
  The first n rows ordered by the given columns in descending
  order.
* **Return type:**
  [DataFrame](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame)

#### SEE ALSO
[`DataFrame.nsmallest`](maxframe.dataframe.DataFrame.nsmallest.md#maxframe.dataframe.DataFrame.nsmallest)
: Return the first n rows ordered by columns in ascending order.

[`DataFrame.sort_values`](maxframe.dataframe.DataFrame.sort_values.md#maxframe.dataframe.DataFrame.sort_values)
: Sort DataFrame by the values.

[`DataFrame.head`](maxframe.dataframe.DataFrame.head.md#maxframe.dataframe.DataFrame.head)
: Return the first n rows without re-ordering.

### Notes

This function cannot be used with all column types. For example, when
specifying columns with object or category dtypes, `TypeError` is
raised.

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> df = md.DataFrame({'population': [59000000, 65000000, 434000,
...                                   434000, 434000, 337000, 11300,
...                                   11300, 11300],
...                    'GDP': [1937894, 2583560 , 12011, 4520, 12128,
...                            17036, 182, 38, 311],
...                    'alpha-2': ["IT", "FR", "MT", "MV", "BN",
...                                "IS", "NR", "TV", "AI"]},
...                   index=["Italy", "France", "Malta",
...                          "Maldives", "Brunei", "Iceland",
...                          "Nauru", "Tuvalu", "Anguilla"])
>>> df.execute()
          population      GDP alpha-2
Italy       59000000  1937894      IT
France      65000000  2583560      FR
Malta         434000    12011      MT
Maldives      434000     4520      MV
Brunei        434000    12128      BN
Iceland       337000    17036      IS
Nauru          11300      182      NR
Tuvalu         11300       38      TV
Anguilla       11300      311      AI
```

In the following example, we will use `nlargest` to select the three
rows having the largest values in column “population”.

```pycon
>>> df.nlargest(3, 'population').execute()
        population      GDP alpha-2
France    65000000  2583560      FR
Italy     59000000  1937894      IT
Malta       434000    12011      MT
```

When using `keep='last'`, ties are resolved in reverse order:

```pycon
>>> df.nlargest(3, 'population', keep='last').execute()
        population      GDP alpha-2
France    65000000  2583560      FR
Italy     59000000  1937894      IT
Brunei      434000    12128      BN
```

When using `keep='all'`, all duplicate items are maintained:

```pycon
>>> df.nlargest(3, 'population', keep='all').execute()
          population      GDP alpha-2
France      65000000  2583560      FR
Italy       59000000  1937894      IT
Malta         434000    12011      MT
Maldives      434000     4520      MV
Brunei        434000    12128      BN
```

To order by the largest values in column “population” and then “GDP”,
we can specify multiple columns like in the next example.

```pycon
>>> df.nlargest(3, ['population', 'GDP']).execute()
        population      GDP alpha-2
France    65000000  2583560      FR
Italy     59000000  1937894      IT
Brunei      434000    12128      BN
```
