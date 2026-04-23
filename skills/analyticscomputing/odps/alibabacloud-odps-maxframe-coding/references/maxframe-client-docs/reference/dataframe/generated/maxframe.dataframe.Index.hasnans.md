# maxframe.dataframe.Index.hasnans

#### *property* Index.hasnans

Return True if there are any NaNs.

* **Return type:**
  [bool](https://docs.python.org/3/library/functions.html#bool)

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> idx = md.Index([1, 2, 3, None])
>>> idx.execute()
Index([1.0, 2.0, 3.0, nan], dtype='float64')
>>> idx.hasnans.execute()
True
```
