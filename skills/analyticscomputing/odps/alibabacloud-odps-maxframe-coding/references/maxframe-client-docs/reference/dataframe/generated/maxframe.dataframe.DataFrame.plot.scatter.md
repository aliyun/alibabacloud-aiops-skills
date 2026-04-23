# maxframe.dataframe.DataFrame.plot.scatter

#### DataFrame.plot.scatter(\*args, \*\*kwargs)

Create a scatter plot with varying marker point size and color.

The coordinates of each point are defined by two dataframe columns and
filled circles are used to represent each point. This kind of plot is
useful to see complex correlations between two variables. Points could
be for instance natural 2D coordinates like longitude and latitude in
a map or, in general, any pair of metrics that can be plotted against
each other.

* **Parameters:**
  * **x** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*str*](https://docs.python.org/3/library/stdtypes.html#str)) – The column name or column position to be used as horizontal
    coordinates for each point.
  * **y** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*str*](https://docs.python.org/3/library/stdtypes.html#str)) – The column name or column position to be used as vertical
    coordinates for each point.
  * **s** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *scalar* *or* *array-like* *,* *optional*) – 

    The size of each point. Possible values are:
    - A string with the name of the column to be used for marker’s size.
    - A single scalar so all points have the same size.
    - A sequence of scalars, which will be used for each point’s size
      recursively. For instance, when passing [2,14] all points size
      will be either 2 or 14, alternatively.
  * **c** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* [*int*](https://docs.python.org/3/library/functions.html#int) *or* *array-like* *,* *optional*) – 

    The color of each point. Possible values are:
    - A single color string referred to by name, RGB or RGBA code,
      for instance ‘red’ or ‘#a98d19’.
    - A sequence of color strings referred to by name, RGB or RGBA
      code, which will be used for each point’s color recursively. For
      instance [‘green’,’yellow’] all points will be filled in green or
      yellow, alternatively.
    - A column name or position whose values will be used to color the
      marker points according to a colormap.
  * **\*\*kwargs** – Keyword arguments to pass on to [`DataFrame.plot()`](maxframe.dataframe.DataFrame.plot.md#maxframe.dataframe.DataFrame.plot).
* **Return type:**
  [`matplotlib.axes.Axes`](https://matplotlib.org/stable/api/_as_gen/matplotlib.axes.Axes.html#matplotlib.axes.Axes) or numpy.ndarray of them

#### SEE ALSO
[`matplotlib.pyplot.scatter`](https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.scatter.html#matplotlib.pyplot.scatter)
: Scatter plot using multiple input data formats.

### Examples

Let’s see how to draw a scatter plot using coordinates from the values
in a DataFrame’s columns.

And now with the color determined by a column as well.
