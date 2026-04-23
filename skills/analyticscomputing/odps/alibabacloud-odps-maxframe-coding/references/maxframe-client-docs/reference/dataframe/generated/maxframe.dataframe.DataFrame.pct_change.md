# maxframe.dataframe.DataFrame.pct_change

#### DataFrame.pct_change(periods=1, fill_method='pad', limit=None, freq=None, \*\*kwargs)

Percentage change between the current and a prior element.

Computes the percentage change from the immediately previous row by
default. This is useful in comparing the percentage of change in a time
series of elements.

* **Parameters:**
  * **periods** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *default 1*) – Periods to shift for forming percent change.
  * **fill_method** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *default 'pad'*) – How to handle NAs before computing percent changes.
  * **limit** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *default None*) – The number of consecutive NAs to fill before stopping.
  * **freq** (*DateOffset* *,* *timedelta* *, or* [*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *optional*) – Increment to use from time series API (e.g. ‘M’ or BDay()).
  * **\*\*kwargs** – Additional keyword arguments are passed into
    DataFrame.shift or Series.shift.
* **Returns:**
  **chg** – The same type as the calling object.
* **Return type:**
  [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series) or [DataFrame](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame)

#### SEE ALSO
`Series.diff`
: Compute the difference of two elements in a Series.

[`DataFrame.diff`](maxframe.dataframe.DataFrame.diff.md#maxframe.dataframe.DataFrame.diff)
: Compute the difference of two elements in a DataFrame.

[`Series.shift`](maxframe.dataframe.Series.shift.md#maxframe.dataframe.Series.shift)
: Shift the index by some number of periods.

[`DataFrame.shift`](maxframe.dataframe.DataFrame.shift.md#maxframe.dataframe.DataFrame.shift)
: Shift the index by some number of periods.
