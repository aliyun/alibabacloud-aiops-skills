# maxframe.dataframe.DataFrame.plot.box

#### DataFrame.plot.box(\*args, \*\*kwargs)

Make a box plot of the DataFrame columns.

A box plot is a method for graphically depicting groups of numerical
data through their quartiles.
The box extends from the Q1 to Q3 quartile values of the data,
with a line at the median (Q2). The whiskers extend from the edges
of box to show the range of the data. The position of the whiskers
is set by default to 1.5\*IQR (IQR = Q3 - Q1) from the edges of the
box. Outlier points are those past the end of the whiskers.

For further details see Wikipedia’s
entry for [boxplot](https://en.wikipedia.org/wiki/Box_plot).

A consideration when using this chart is that the box and the whiskers
can overlap, which is very common when plotting small sets of data.

* **Parameters:**
  * **by** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *or* *sequence*) – 

    Column in the DataFrame to group by.

    #### Versionchanged
    Changed in version 1.4.0: Previously, by is silently ignore and makes no groupings
  * **\*\*kwargs** – Additional keywords are documented in
    [`DataFrame.plot()`](maxframe.dataframe.DataFrame.plot.md#maxframe.dataframe.DataFrame.plot).
* **Return type:**
  [`matplotlib.axes.Axes`](https://matplotlib.org/stable/api/_as_gen/matplotlib.axes.Axes.html#matplotlib.axes.Axes) or numpy.ndarray of them

#### SEE ALSO
`DataFrame.boxplot`
: Another method to draw a box plot.

[`Series.plot.box`](maxframe.dataframe.Series.plot.box.md#maxframe.dataframe.Series.plot.box)
: Draw a box plot from a Series object.

[`matplotlib.pyplot.boxplot`](https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.boxplot.html#matplotlib.pyplot.boxplot)
: Draw a box plot in matplotlib.

### Examples

Draw a box plot from a DataFrame with four columns of randomly
generated data.

You can also generate groupings if you specify the by parameter (which
can take a column name, or a list or tuple of column names):

#### Versionchanged
Changed in version 1.4.0.
