# maxframe.dataframe.DataFrame.plot.area

#### DataFrame.plot.area(\*args, \*\*kwargs)

Draw a stacked area plot.

An area plot displays quantitative data visually.
This function wraps the matplotlib area function.

* **Parameters:**
  * **x** (*label* *or* *position* *,* *optional*) – Coordinates for the X axis. By default uses the index.
  * **y** (*label* *or* *position* *,* *optional*) – Column to plot. By default uses all columns.
  * **stacked** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default True*) – Area plots are stacked by default. Set to False to create a
    unstacked plot.
  * **\*\*kwargs** – Additional keyword arguments are documented in
    [`DataFrame.plot()`](maxframe.dataframe.DataFrame.plot.md#maxframe.dataframe.DataFrame.plot).
* **Returns:**
  Area plot, or array of area plots if subplots is True.
* **Return type:**
  [matplotlib.axes.Axes](https://matplotlib.org/stable/api/_as_gen/matplotlib.axes.Axes.html#matplotlib.axes.Axes) or [numpy.ndarray](https://numpy.org/doc/stable/reference/generated/numpy.ndarray.html#numpy.ndarray)

#### SEE ALSO
[`DataFrame.plot`](maxframe.dataframe.DataFrame.plot.md#maxframe.dataframe.DataFrame.plot)
: Make plots of DataFrame using matplotlib / pylab.

### Examples

Draw an area plot based on basic business metrics:

Area plots are stacked by default. To produce an unstacked plot,
pass `stacked=False`:

Draw an area plot for a single column:

Draw with a different x:
