# maxframe.dataframe.Series.plot.pie

#### Series.plot.pie(\*args, \*\*kwargs)

Generate a pie plot.

A pie plot is a proportional representation of the numerical data in a
column. This function wraps `matplotlib.pyplot.pie()` for the
specified column. If no column reference is passed and
`subplots=True` a pie plot is drawn for each numerical column
independently.

* **Parameters:**
  * **y** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* *label* *,* *optional*) – Label or position of the column to plot.
    If not provided, `subplots=True` argument must be passed.
  * **\*\*kwargs** – Keyword arguments to pass on to [`DataFrame.plot()`](maxframe.dataframe.DataFrame.plot.md#maxframe.dataframe.DataFrame.plot).
* **Returns:**
  A NumPy array is returned when subplots is True.
* **Return type:**
  [matplotlib.axes.Axes](https://matplotlib.org/stable/api/_as_gen/matplotlib.axes.Axes.html#matplotlib.axes.Axes) or np.ndarray of them

#### SEE ALSO
[`Series.plot.pie`](#maxframe.dataframe.Series.plot.pie)
: Generate a pie plot for a Series.

[`DataFrame.plot`](maxframe.dataframe.DataFrame.plot.md#maxframe.dataframe.DataFrame.plot)
: Make plots of a DataFrame.

### Examples

In the example below we have a DataFrame with the information about
planet’s mass and radius. We pass the ‘mass’ column to the
pie function to get a pie plot.
