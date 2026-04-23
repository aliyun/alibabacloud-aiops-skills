# maxframe.dataframe.Series.to_frame

#### Series.to_frame(name=None)

Convert Series to DataFrame.

* **Parameters:**
  **name** ([*object*](https://docs.python.org/3/library/functions.html#object) *,* *default None*) – The passed name should substitute for the series name (if it has
  one).
* **Returns:**
  DataFrame representation of Series.
* **Return type:**
  [DataFrame](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame)

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> s = md.Series(["a", "b", "c"], name="vals")
>>> s.to_frame().execute()
  vals
0    a
1    b
2    c
```
