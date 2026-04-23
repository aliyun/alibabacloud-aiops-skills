# maxframe.dataframe.Series.tshift

#### Series.tshift(periods: [int](https://docs.python.org/3/library/functions.html#int) = 1, freq=None, axis=0)

Shift the time index, using the index’s frequency if available.

* **Parameters:**
  * **periods** ([*int*](https://docs.python.org/3/library/functions.html#int)) – Number of periods to move, can be positive or negative.
  * **freq** (*DateOffset* *,* *timedelta* *, or* [*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *default None*) – Increment to use from the tseries module
    or time rule expressed as a string (e.g. ‘EOM’).
  * **axis** ( *{0* *or*  *‘index’* *,* *1* *or*  *‘columns’* *,* *None}* *,* *default 0*) – Corresponds to the axis that contains the Index.
* **Returns:**
  **shifted**
* **Return type:**
  Series/DataFrame

### Notes

If freq is not specified then tries to use the freq or inferred_freq
attributes of the index. If neither of those attributes exist, a
ValueError is thrown
