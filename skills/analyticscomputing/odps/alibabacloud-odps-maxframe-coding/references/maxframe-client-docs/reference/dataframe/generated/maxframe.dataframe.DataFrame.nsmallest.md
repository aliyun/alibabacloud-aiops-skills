# maxframe.dataframe.DataFrame.nsmallest

#### DataFrame.nsmallest(n, columns, keep='first')

Return the first n rows ordered by columns in ascending order.

Return the first n rows with the smallest values in columns, in
ascending order. The columns that are not specified are returned as
well, but not used for ordering.

This method is equivalent to
`df.sort_values(columns, ascending=True).head(n)`, but more
performant.

* **Parameters:**
  * **n** ([*int*](https://docs.python.org/3/library/functions.html#int)) – Number of items to retrieve.
  * **columns** ([*list*](https://docs.python.org/3/library/stdtypes.html#list) *or* [*str*](https://docs.python.org/3/library/stdtypes.html#str)) – Column name or names to order by.
  * **keep** ( *{'first'* *,*  *'last'* *,*  *'all'}* *,* *default 'first'*) – 

    Where there are duplicate values:
    - `first` : take the first occurrence.
    - `last` : take the last occurrence.
    - `all` : do not drop any duplicates, even it means
      selecting more than n items.
* **Return type:**
  [DataFrame](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame)

#### SEE ALSO
[`DataFrame.nlargest`](maxframe.dataframe.DataFrame.nlargest.md#maxframe.dataframe.DataFrame.nlargest)
: Return the first n rows ordered by columns in descending order.

[`DataFrame.sort_values`](maxframe.dataframe.DataFrame.sort_values.md#maxframe.dataframe.DataFrame.sort_values)
: Sort DataFrame by the values.

[`DataFrame.head`](maxframe.dataframe.DataFrame.head.md#maxframe.dataframe.DataFrame.head)
: Return the first n rows without re-ordering.

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> df = md.DataFrame({'population': [59000000, 65000000, 434000,
...                                   434000, 434000, 337000, 337000,
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
Nauru         337000      182      NR
Tuvalu         11300       38      TV
Anguilla       11300      311      AI
```

In the following example, we will use `nsmallest` to select the
three rows having the smallest values in column “population”.

```pycon
>>> df.nsmallest(3, 'population').execute()
          population    GDP alpha-2
Tuvalu         11300     38      TV
Anguilla       11300    311      AI
Iceland       337000  17036      IS
```

When using `keep='last'`, ties are resolved in reverse order:

```pycon
>>> df.nsmallest(3, 'population', keep='last').execute()
          population  GDP alpha-2
Anguilla       11300  311      AI
Tuvalu         11300   38      TV
Nauru         337000  182      NR
```

When using `keep='all'`, all duplicate items are maintained:

```pycon
>>> df.nsmallest(3, 'population', keep='all').execute()
          population    GDP alpha-2
Tuvalu         11300     38      TV
Anguilla       11300    311      AI
Iceland       337000  17036      IS
Nauru         337000    182      NR
```

To order by the smallest values in column “population” and then “GDP”, we can
specify multiple columns like in the next example.

```pycon
>>> df.nsmallest(3, ['population', 'GDP']).execute()
          population  GDP alpha-2
Tuvalu         11300   38      TV
Anguilla       11300  311      AI
Nauru         337000  182      NR
```
