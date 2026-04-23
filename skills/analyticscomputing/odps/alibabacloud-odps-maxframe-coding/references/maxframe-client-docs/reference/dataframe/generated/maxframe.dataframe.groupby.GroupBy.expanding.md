# maxframe.dataframe.groupby.GroupBy.expanding

#### GroupBy.expanding(min_periods=1, , shift=0, reverse_range=False, order_cols=None, ascending=True)

Return an expanding grouper, providing expanding
functionality per group.

* **Parameters:**
  * **min_periods** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *default None*) – Minimum number of observations in window required to have a value;
    otherwise, result is `np.nan`.
  * **shift** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *default 0*) – If specified, the window will be shifted by shift rows (or data will be
    shifted by -shift rows) before computing window function.
  * **reverse_range** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default False*) – If True, the window for current row is expanded from the last row to
    the current instead of the first row.
* **Return type:**
  maxframe.dataframe.groupby.ExpandingGroupby

#### SEE ALSO
`Series.groupby`
: Apply a function groupby to a Series.

`DataFrame.groupby`
: Apply a function groupby to each row or column of a DataFrame.
