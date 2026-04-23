# maxframe.dataframe.Series.between

#### Series.between(left, right, inclusive='both')

Return boolean Series equivalent to left <= series <= right.
This function returns a boolean vector containing True wherever the
corresponding Series element is between the boundary values left and
right. NA values are treated as False.

* **Parameters:**
  * **left** (*scalar* *or* *list-like*) – Left boundary.
  * **right** (*scalar* *or* *list-like*) – Right boundary.
  * **inclusive** ( *{"both"* *,*  *"neither"* *,*  *"left"* *,*  *"right"}*) – Include boundaries. Whether to set each bound as closed or open.
* **Returns:**
  Series representing whether each element is between left and
  right (inclusive).
* **Return type:**
  [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series)

#### SEE ALSO
[`Series.gt`](maxframe.dataframe.Series.gt.md#maxframe.dataframe.Series.gt)
: Greater than of series and other.

[`Series.lt`](maxframe.dataframe.Series.lt.md#maxframe.dataframe.Series.lt)
: Less than of series and other.

### Notes

This function is equivalent to `(left <= ser) & (ser <= right)`

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> s = md.Series([2, 0, 4, 8, np.nan])
```

Boundary values are included by default:

```pycon
>>> s.between(1, 4).execute()
0     True
1    False
2     True
3    False
4    False
dtype: bool
```

With inclusive set to `"neither"` boundary values are excluded:

```pycon
>>> s.between(1, 4, inclusive="neither").execute()
0     True
1    False
2    False
3    False
4    False
dtype: bool
```

left and right can be any scalar value:

```pycon
>>> s = md.Series(['Alice', 'Bob', 'Carol', 'Eve'])
>>> s.between('Anna', 'Daniel').execute()
0    False
1     True
2     True
3    False
dtype: bool
```
