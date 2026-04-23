# maxframe.dataframe.Index.is_unique

#### *property* Index.is_unique

Return boolean if values in the index are unique.

* **Return type:**
  [bool](https://docs.python.org/3/library/functions.html#bool)

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> index = md.Index([1, 2, 3])
>>> index.is_unique.execute()
True
```

```pycon
>>> index = md.Index([1, 2, 3, 1])
>>> index.is_unique.execute()
False
```
