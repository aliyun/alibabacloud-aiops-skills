# maxframe.dataframe.Series.combine_first

#### Series.combine_first(other)

Update null elements with value in the same location in ‘other’.

Combine two Series objects by filling null values in one Series with
non-null values from the other Series. Result index will be the union
of the two indexes.

* **Parameters:**
  **other** ([*Series*](maxframe.dataframe.Series.md#maxframe.dataframe.Series)) – The value(s) to be used for filling null values.
* **Returns:**
  The result of combining the provided Series with the other object.
* **Return type:**
  [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series)

#### SEE ALSO
[`Series.combine`](maxframe.dataframe.Series.combine.md#maxframe.dataframe.Series.combine)
: Perform element-wise operation on two Series using a given function.

### Examples

```pycon
>>> import maxframe.tensor as mt
>>> import maxframe.dataframe as md
>>> s1 = md.Series([1, mt.nan])
>>> s2 = md.Series([3, 4, 5])
>>> s1.combine_first(s2).execute()
0    1.0
1    4.0
2    5.0
dtype: float64
```

Null values still persist if the location of that null value
does not exist in other

```pycon
>>> s1 = md.Series({'falcon': mt.nan, 'eagle': 160.0})
>>> s2 = md.Series({'eagle': 200.0, 'duck': 30.0})
>>> s1.combine_first(s2).execute()
duck       30.0
eagle     160.0
falcon      NaN
dtype: float64
```
