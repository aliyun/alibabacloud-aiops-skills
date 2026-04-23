# maxframe.dataframe.Series.reorder_levels

#### Series.reorder_levels(order)

Rearrange index levels using input order.

May not drop or duplicate levels.

* **Parameters:**
  **order** ([*list*](https://docs.python.org/3/library/stdtypes.html#list) *of* *int representing new level order*) – Reference level by number or key.
* **Return type:**
  [type](https://docs.python.org/3/library/functions.html#type) of caller (new object)

### Examples

```pycon
>>> import maxframe.tensor as mt
>>> import maxframe.dataframe as md
>>> arrays = [mt.array(["dog", "dog", "cat", "cat", "bird", "bird"]),
...           mt.array(["white", "black", "white", "black", "white", "black"])]
>>> s = md.Series([1, 2, 3, 3, 5, 2], index=arrays)
>>> s.execute()
dog   white    1
      black    2
cat   white    3
      black    3
bird  white    5
      black    2
dtype: int64
>>> s.reorder_levels([1, 0]).execute()
white  dog     1
black  dog     2
white  cat     3
black  cat     3
white  bird    5
black  bird    2
dtype: int64
```
