# maxframe.dataframe.DataFrame.plot.bar

#### DataFrame.plot.bar(\*args, \*\*kwargs)

Vertical bar plot.

A bar plot is a plot that presents categorical data with
rectangular bars with lengths proportional to the values that they
represent. A bar plot shows comparisons among discrete categories. One
axis of the plot shows the specific categories being compared, and the
other axis represents a measured value.

* **Parameters:**
  * **x** (*label* *or* *position* *,* *optional*) – Allows plotting of one column versus another. If not specified,
    the index of the DataFrame is used.
  * **y** (*label* *or* *position* *,* *optional*) – Allows plotting of one column versus another. If not specified,
    all numerical columns are used.
  * **color** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *array-like* *, or* [*dict*](https://docs.python.org/3/library/stdtypes.html#dict) *,* *optional*) – 

    The color for each of the DataFrame’s columns. Possible values are:
    - A single color string referred to by name, RGB or RGBA code,
      : for instance ‘red’ or ‘#a98d19’.
    - A sequence of color strings referred to by name, RGB or RGBA
      : code, which will be used for each column recursively. For
        instance [‘green’,’yellow’] each column’s bar will be filled in
        green or yellow, alternatively. If there is only a single column to
        be plotted, then only the first color from the color list will be
        used.
    - A dict of the form {column name
      : colored accordingly. For example, if your columns are called a and
        b, then passing {‘a’: ‘green’, ‘b’: ‘red’} will color bars for
        column a in green and bars for column b in red.
  * **\*\*kwargs** – Additional keyword arguments are documented in
    [`DataFrame.plot()`](maxframe.dataframe.DataFrame.plot.md#maxframe.dataframe.DataFrame.plot).
* **Returns:**
  An ndarray is returned with one [`matplotlib.axes.Axes`](https://matplotlib.org/stable/api/_as_gen/matplotlib.axes.Axes.html#matplotlib.axes.Axes)
  per column when `subplots=True`.
  > DataFrame.plot.barh : Horizontal bar plot.
  > DataFrame.plot : Make plots of a DataFrame.
  > matplotlib.pyplot.bar : Make a bar plot with matplotlib.

  > Basic plot.

  > Plot a whole dataframe to a bar plot. Each column is assigned a
  > distinct color, and each row is nested in a group along the
  > horizontal axis.

  > Plot stacked bar charts for the DataFrame

  > Instead of nesting, the figure can be split by column with
  > `subplots=True`. In this case, a [`numpy.ndarray`](https://numpy.org/doc/stable/reference/generated/numpy.ndarray.html#numpy.ndarray) of
  > [`matplotlib.axes.Axes`](https://matplotlib.org/stable/api/_as_gen/matplotlib.axes.Axes.html#matplotlib.axes.Axes) are returned.

  > If you don’t like the default colours, you can specify how you’d
  > like each column to be colored.

  > Plot a single column.

  > Plot only selected categories for the DataFrame.
* **Return type:**
  [matplotlib.axes.Axes](https://matplotlib.org/stable/api/_as_gen/matplotlib.axes.Axes.html#matplotlib.axes.Axes) or np.ndarray of them
