# maxframe.dataframe.DataFrame.head

#### DataFrame.head(n=5)

Return the first n rows.

This function returns the first n rows for the object based
on position. It is useful for quickly testing if your object
has the right type of data in it.

For negative values of n, this function returns all rows except
the last n rows, equivalent to `df[:-n]`.

* **Parameters:**
  **n** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *default 5*) – Number of rows to select.
* **Returns:**
  The first n rows of the caller object.
* **Return type:**
  same type as caller

#### SEE ALSO
[`DataFrame.tail`](maxframe.dataframe.DataFrame.tail.md#maxframe.dataframe.DataFrame.tail)
: Returns the last n rows.

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> df = md.DataFrame({'animal': ['alligator', 'bee', 'falcon', 'lion',
...                    'monkey', 'parrot', 'shark', 'whale', 'zebra']})
>>> df.execute()
      animal
0  alligator
1        bee
2     falcon
3       lion
4     monkey
5     parrot
6      shark
7      whale
8      zebra
```

Viewing the first 5 lines

```pycon
>>> df.head().execute()
      animal
0  alligator
1        bee
2     falcon
3       lion
4     monkey
```

Viewing the first n lines (three in this case)

```pycon
>>> df.head(3).execute()
      animal
0  alligator
1        bee
2     falcon
```

For negative values of n

```pycon
>>> df.head(-3).execute()
      animal
0  alligator
1        bee
2     falcon
3       lion
4     monkey
5     parrot
```
