# maxframe.dataframe.Series.is_unique

#### *property* Series.is_unique

Return boolean if values in the object are unique.

* **Return type:**
  [bool](https://docs.python.org/3/library/functions.html#bool)

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> s = md.Series([1, 2, 3])
>>> s.is_unique.execute()
True
```

```pycon
>>> s = md.Series([1, 2, 3, 1])
>>> s.is_unique.execute()
False
```
