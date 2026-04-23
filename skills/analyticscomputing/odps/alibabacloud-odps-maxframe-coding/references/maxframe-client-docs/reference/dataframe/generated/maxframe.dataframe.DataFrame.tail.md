# maxframe.dataframe.DataFrame.tail

#### DataFrame.tail(n=5)

Return the last n rows.

This function returns last n rows from the object based on
position. It is useful for quickly verifying data, for example,
after sorting or appending rows.

For negative values of n, this function returns all rows except
the first n rows, equivalent to `df[n:]`.

* **Parameters:**
  **n** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *default 5*) – Number of rows to select.
* **Returns:**
  The last n rows of the caller object.
* **Return type:**
  [type](https://docs.python.org/3/library/functions.html#type) of caller

#### SEE ALSO
[`DataFrame.head`](maxframe.dataframe.DataFrame.head.md#maxframe.dataframe.DataFrame.head)
: The first n rows of the caller object.

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

Viewing the last 5 lines

```pycon
>>> df.tail().execute()
   animal
4  monkey
5  parrot
6   shark
7   whale
8   zebra
```

Viewing the last n lines (three in this case)

```pycon
>>> df.tail(3).execute()
  animal
6  shark
7  whale
8  zebra
```

For negative values of n

```pycon
>>> df.tail(-3).execute()
   animal
3    lion
4  monkey
5  parrot
6   shark
7   whale
8   zebra
```
